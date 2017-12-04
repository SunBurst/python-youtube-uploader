#!/usr/bin/python

import argparse
import dateutil.parser
import httplib2
import os
import sys

from apiclient.discovery import build
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow


# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the {{ Google Cloud Console }} at
# {{ https://cloud.google.com/console }}.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
CLIENT_SECRETS_FILE = "client_secrets.json"

# This variable defines a message to display if the CLIENT_SECRETS_FILE is
# missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the {{ Cloud Console }}
{{ https://cloud.google.com/console }}

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   CLIENT_SECRETS_FILE))

# This OAuth 2.0 access scope allows for read-only access to the authenticated
# user's account, but not other types of account access.
YOUTUBE_READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

def export_my_uploads(args):

    flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE,
      message=MISSING_CLIENT_SECRETS_MESSAGE,
      scope=YOUTUBE_READONLY_SCOPE)

    storage = Storage("%s-oauth2.json" % sys.argv[0])
    credentials = storage.get()

    if credentials is None or credentials.invalid:
      flags = argparser.parse_args()
      credentials = run_flow(flow, storage, flags)

    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
      http=credentials.authorize(httplib2.Http()))

    # Retrieve the contentDetails part of the channel resource for the
    # authenticated user's channel.
    channels_response = youtube.channels().list(
      mine=True,
      part="contentDetails"
    ).execute()

    for channel in channels_response["items"]:
      # From the API response, extract the playlist ID that identifies the list
      # of videos uploaded to the authenticated user's channel.
      uploads_list_id = channel["contentDetails"]["relatedPlaylists"]["uploads"]
      print("Videos in list %s" % uploads_list_id)
      channel_file = os.path.join(args.output_directory, uploads_list_id + '.csv')
      channel_video_urls = []
      # Retrieve the list of videos uploaded to the authenticated user's channel.
      playlistitems_list_request = youtube.playlistItems().list(
        playlistId=uploads_list_id,
        part="snippet",
        maxResults=50
      )
      video_counter = 0
      while playlistitems_list_request:
        playlistitems_list_response = playlistitems_list_request.execute()
        # Print information about each video.
        for playlist_item in playlistitems_list_response["items"]:
          video_counter += 1
          if isinstance(args.limit, int) and video_counter > args.limit:
            break
          title = playlist_item["snippet"]["title"]
          published_at = playlist_item["snippet"]["publishedAt"]
          video_id = playlist_item["snippet"]["resourceId"]["videoId"]
          published_at_dt = dateutil.parser.parse(published_at)
          published_at_dt_str = published_at_dt.strftime("%Y-%m-%d%z")
          video_link = "https://youtu.be/{}".format(video_id)
          row = {
            'added_date': published_at_dt_str,
            'video_url': video_link
          }
          channel_video_urls.append(row)
        if isinstance(args.limit, int) and video_counter > args.limit:
          break
        playlistitems_list_request = youtube.playlistItems().list_next(
          playlistitems_list_request, playlistitems_list_response)
        
      if not os.path.exists(args.output_directory):
        os.makedirs(args.output_directory)
      with open(channel_file, 'a+') as f:
        for row in channel_video_urls:
          f.write("{added_date}, {video_url}\n".format(
            added_date=row.get('added_date'), video_url=row.get('video_url')))

if __name__=='__main__':
    """Parses and validates arguments from the command line. """
    parser = argparse.ArgumentParser(
        prog='YoutubeVideoUrlsExporter',
        description='Program for exporting Youtube video urls.'
    )
    parser.add_argument('-l', '--limit', type=int, action='store', dest='limit',
                        help='Number of urls to process.')
    parser.add_argument('-d', '--outputdir', action='store', dest='output_directory',
                        help='File output directory.')

    args = parser.parse_args()
    
    if not args.output_directory:
        parser.error('--outputdir is required.')
    
    export_my_uploads(args)
