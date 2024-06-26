# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Utilities for the cloudbuild v2 API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base
from googlecloudsdk.core import resources
from googlecloudsdk.core.resource import resource_property

_API_NAME = 'cloudbuild'
GA_API_VERSION = 'v2'

RELEASE_TRACK_TO_API_VERSION = {
    base.ReleaseTrack.GA: GA_API_VERSION,
    base.ReleaseTrack.BETA: GA_API_VERSION,
    base.ReleaseTrack.ALPHA: GA_API_VERSION,
}

CLUSTER_NAME_SELECTOR = r'projects/.*/locations/.*/memberships/(.*)'
WORKERPOOL_SECOND_GEN_NAME_MATCHER = (
    r'projects/.*/locations/.*/workerPoolSecondGen/.*'
)
WORKERPOOL_SECOND_GEN_NAME_SELECTOR = (
    r'projects/.*/locations/.*/workerPoolSecondGen/(.*)'
)


def GetMessagesModule(release_track=base.ReleaseTrack.GA):
  """Returns the messages module for Cloud Build.

  Args:
    release_track: The desired value of the enum
      googlecloudsdk.calliope.base.ReleaseTrack.

  Returns:
    Module containing the definitions of messages for Cloud Build.
  """
  return apis.GetMessagesModule(_API_NAME,
                                RELEASE_TRACK_TO_API_VERSION[release_track])


def GetClientInstance(release_track=base.ReleaseTrack.GA, use_http=True):
  """Returns an instance of the Cloud Build client.

  Args:
    release_track: The desired value of the enum
      googlecloudsdk.calliope.base.ReleaseTrack.
    use_http: bool, True to create an http object for this client.

  Returns:
    base_api.BaseApiClient, An instance of the Cloud Build client.
  """
  return apis.GetClientInstance(
      _API_NAME,
      RELEASE_TRACK_TO_API_VERSION[release_track],
      no_http=(not use_http))


def GetRun(project, region, run_id, run_type):
  """Get a PipelineRun/TaskRun."""
  client = GetClientInstance()
  messages = GetMessagesModule()
  if run_type == 'pipelinerun':
    pipeline_run_resource = resources.REGISTRY.Parse(
        run_id,
        collection='cloudbuild.projects.locations.pipelineRuns',
        api_version='v2',
        params={
            'projectsId': project,
            'locationsId': region,
            'pipelineRunsId': run_id,
        })
    pipeline_run = client.projects_locations_pipelineRuns.Get(
        messages.CloudbuildProjectsLocationsPipelineRunsGetRequest(
            name=pipeline_run_resource.RelativeName(),))
    return pipeline_run
  elif run_type == 'taskrun':
    task_run_resource = resources.REGISTRY.Parse(
        run_id,
        collection='cloudbuild.projects.locations.taskRuns',
        api_version='v2',
        params={
            'projectsId': project,
            'locationsId': region,
            'taskRunsId': run_id,
        })
    task_run = client.projects_locations_taskRuns.Get(
        messages.CloudbuildProjectsLocationsTaskRunsGetRequest(
            name=task_run_resource.RelativeName(),))
    return task_run


def ClusterShortName(resource_name):
  """Get the name part of a cluster membership's full resource name.

  For example, "projects/123/locations/global/memberships/cluster2" returns
  "cluster2".

  Args:
    resource_name: A cluster's full resource name.

  Raises:
    ValueError: If the full resource name was not well-formatted.

  Returns:
    The cluster's short name.
  """
  match = re.search(CLUSTER_NAME_SELECTOR, resource_name)
  if match:
    return match.group(1)
  raise ValueError('The cluster membership resource name must match "%s"' %
                   (CLUSTER_NAME_SELECTOR,))


def ListLocations(project):
  """Get the list of supported Cloud Build locations.

  Args:
    project: The project to search.

  Returns:
    A CloudbuildProjectsLocationsListRequest object.
  """
  client = GetClientInstance()
  messages = GetMessagesModule()

  return client.projects_locations.List(
      messages.CloudbuildProjectsLocationsListRequest(
          name='projects/{}'.format(project)
      )
  )


def WorkerPoolSecondGenShortName(resource_name):
  """Get the name part of a worker pool second gen's full resource name.

  E.g. "projects/abc/locations/def/workerPoolSecondGen/ghi" returns "ghi".

  Args:
    resource_name: A worker pool second gen's full resource name.

  Raises:
    ValueError: If the full resource name was not well-formatted.

  Returns:
    The worker pool's short name.
  """
  match = re.search(WORKERPOOL_SECOND_GEN_NAME_SELECTOR, resource_name)
  if match:
    return match.group(1)
  raise ValueError('The worker pool second gen resource name must match "%s"' %
                   (WORKERPOOL_SECOND_GEN_NAME_MATCHER,))


def MessageToFieldPaths(msg):
  """Produce field paths from a message object.

  The result is used to create a FieldMask proto message that contains all field
  paths presented in the object.
  https://github.com/protocolbuffers/protobuf/blob/master/src/google/protobuf/field_mask.proto

  Args:
    msg: A user defined message object that extends the messages.Message class.
    https://github.com/google/apitools/blob/master/apitools/base/protorpclite/messages.py

  Returns:
    The list of field paths.
  """
  fields = []
  for field in msg.all_fields():
    v = msg.get_assigned_value(field.name)
    if field.repeated and not v:
      # Repeated field is initialized as an empty list.
      continue
    if v is not None:
      name = resource_property.ConvertToSnakeCase(field.name)
      if hasattr(v, 'all_fields'):
        # message has sub-messages, constructing subpaths.
        for f in MessageToFieldPaths(v):
          fields.append('{}.{}'.format(name, f))
      else:
        fields.append(name)
  return fields
