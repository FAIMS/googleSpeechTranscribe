#!/usr/bin/env python

# Copyright 2017 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Google Cloud Speech API sample application using the REST API for async
batch processing.

Example usage:
    python transcribe_async.py resources/audio.raw
    python transcribe_async.py gs://cloud-samples-tests/speech/vr.flac
"""

import argparse
import io
import time
import os
import progressbar
import ffmpy
import tempfile
import contextlib

from google.cloud import storage

@contextlib.contextmanager
def cd(newdir, cleanup=lambda: True):
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)
        cleanup()

@contextlib.contextmanager
def tempdir():
    dirpath = tempfile.mkdtemp()
    def cleanup():
        shutil.rmtree(dirpath)
    with cd(dirpath, cleanup):
        yield dirpath

def delete_blob(bucket_name, blob_name):
    """Deletes a blob from the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)

    blob.delete()

    print('Blob {} deleted.'.format(blob_name))

def upload_blob(bucket_name, source_file_name):
    """Uploads a file to the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    filename, file_extensions = os.path.splitext(source_file_name)
    destName = '%s%s' % (time.mktime(time.gmtime()), file_extensions)

    print("Uploading %s" % (source_file_name))

    blob = bucket.blob(destName)
    blob.upload_from_filename(source_file_name)

    print('File {} uploaded to {}/{}'.format(
        source_file_name,
        bucket_name, destName))

    return ('gs://%s/%s' % (bucket_name, destName), destName)
    
def transcribe_file(speech_file):
    """Transcribe the given audio file asynchronously."""
    from google.cloud import speech
    speech_client = speech.Client()


    """
    with io.open(speech_file, 'rb') as audio_file:
        content = audio_file.read()
        audio_sample = speech_client.sample(
            content,
            source_uri=None,
            encoding=speech.Encoding.FLAC,
            sample_rate_hertz=48000)
    """
    basename = os.path.basename(speech_file)
    filename, file_extensions = os.path.splitext(basename)

    try:
      path, blobName = upload_blob('audio-transcripts-regional', speech_file)

      audio_sample = speech_client.sample(
          content=None,
          source_uri=path,
          encoding='FLAC',
          sample_rate_hertz=48000)

      operation = audio_sample.long_running_recognize('en-AU',max_alternatives=4)



      max_retry_count = 100000
      retry_count = 0
      with progressbar.ProgressBar(max_value=progressbar.UnknownLength) as bar:    
        while retry_count < max_retry_count and not operation.complete:
            retry_count += 1
            bar.update(retry_count)
            time.sleep(2)
            operation.poll()

      if not operation.complete:
          print('Operation not complete and retry limit reached.')
          return

      alternatives = operation.results

     
      with open('tmpOut/%s.tsv' % (basename), 'w+' ) as file:
        for i, alternative in enumerate(alternatives):
          file.write('{}\t'.format(alternative.transcript))
          file.write('{}\n'.format(alternative.confidence))
      # [END send_request]
    finally:
      print("Cleaning up %s" % (blobName))
      delete_blob('audio-transcripts-regional', blobName)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        'path', help='File or GCS path for audio file to be recognized')
    args = parser.parse_args()
    transcribe_file(args.path)
