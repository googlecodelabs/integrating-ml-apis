#!/usr/bin/env python

# Copyright 2018 Google Inc. All Rights Reserved.
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

import argparse
from google.cloud import vision
from google.cloud import speech
from google.cloud import translate
from google.cloud import language
from google.cloud.language import enums
import six

def detect_labels_uri(uri):
    """Detects labels in the file located in Google Cloud Storage or on the
    Web."""

    # create ImageAnnotatorClient object
    client = vision.ImageAnnotatorClient()

    # create Image object
    image = vision.types.Image()

    # specify location of image
    image.source.image_uri = uri

    # get label_detection response by passing image to client
    response = client.label_detection(image=image)

    # get label_annotations portion of response
    labels = response.label_annotations

    # we only need the label descriptions
    label_descriptions = []
    for label in labels:
        label_descriptions.append(label.description)
        
    return label_descriptions

def transcribe_gcs(language, gcs_uri):
    """Transcribes the audio file specified by the gcs_uri."""

    # create ImageAnnotatorClient object
    client = speech.SpeechClient()

    # specify location of speech
    audio = speech.types.RecognitionAudio(uri=gcs_uri) # need to specify speech.types

    # set language to Turkish
    # removed encoding and sample_rate_hertz
    config = speech.types.RecognitionConfig(language_code=language) # need to specify speech.types

    # get response by passing config and audio settings to client
    response = client.recognize(config, audio)

    # naive assumption that audio file is short
    return response.results[0].alternatives[0].transcript

def translate_text(target, text):
    """Translates text into the target language.

    Target must be an ISO 639-1 language code.
    See https://g.co/cloud/translate/v2/translate-reference#supported_languages
    """

    # create Client object
    translate_client = translate.Client()

    # decode text if it's a binary type
    if isinstance(text, six.binary_type):
        text = text.decode('utf-8')

    # get translation result by passing text and target language to client
    # Text can also be a sequence of strings, in which case this method
    # will return a sequence of results for each text.
    result = translate_client.translate(text, target_language=target)

    # only interested in translated text
    return result['translatedText']

def entities_text(text):
    """Detects entities in the text."""

    # create LanguageServiceClient object
    client = language.LanguageServiceClient()

    # decode text if it's a binary type
    if isinstance(text, six.binary_type):
        text = text.decode('utf-8')

    # Instantiates a plain text document.
    # need to specify language.types
    document = language.types.Document(
        content=text,
        type=enums.Document.Type.PLAIN_TEXT)

    # Detects entities in the document. You can also analyze HTML with:
    #   document.type == enums.Document.Type.HTML
    entities = client.analyze_entities(document).entities

    # entity types from enums.Entity.Type
    entity_type = ('UNKNOWN', 'PERSON', 'LOCATION', 'ORGANIZATION',
                   'EVENT', 'WORK_OF_ART', 'CONSUMER_GOOD', 'OTHER')

    # we only need the entity names
    entity_names = []
    for entity in entities:
        entity_names.append(entity.name)

    return entity_names

def compare_audio_to_image(language, audio, image):
    """Checks whether a speech audio is relevant to an image."""

    # speech audio -> text
    transcription = transcribe_gcs(language, audio)

    # text of any language -> english text
    translation = translate_text('en', transcription)

    # text -> entities
    entities = entities_text(translation)

    # image -> labels
    labels = detect_labels_uri(image)

    # naive check for whether entities intersect with labels
    has_match = False
    for entity in entities:
        if entity in labels:
            print('The audio and image both contain: {}'.format(entity))
            has_match = True
    if not has_match:
        print('The audio and image do not appear to be related.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        'language', help='Language code of speech audio')
    parser.add_argument(
        'audio', help='GCS path for audio file to be recognised')
    parser.add_argument(
        'image', help='GCS path for image file to be analysed')
    args = parser.parse_args()
    compare_audio_to_image(args.language, args.audio, args.image)