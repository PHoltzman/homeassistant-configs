import logging
from copy import copy
import random

import requests
import asyncio

from homeassistant.helpers import intent

DOMAIN = 'kodi_wrapper'

logger = logging.getLogger(__name__)

def setup(hass, config):

	base = {
		"jsonrpc": "2.0",
		"id": 1
	}
	
	audio_playlist = 0
	video_playlist = 1
	
	audio_player_type = 'audio'
	video_player_type = 'video'
	
	def wrap_payload(payload):
		d = payload.copy()
		d.update(base)
		return d
	
	def get_url(kodi_location=''):
		if kodi_location == 'bedroom':
			return 'http://192.168.1.4:8085' + '/jsonrpc'
		else:
			return 'http://192.168.1.17:8089' + '/jsonrpc'
			
	def get_entity(kodi_location=''):
		if kodi_location == 'bedroom':
			return 'media_player.bedroom'
		else:
			return 'media_player.downstairs'
	
	
	################## Find Players #######################
	def find_active_player(kodi_location):
		logger.info('Searching for an active player...')
		payload = {
			"method": "Player.GetActivePlayers"
		}
		resp = requests.post(get_url(kodi_location), json=wrap_payload(payload))
		code = resp.status_code
		if code != 200:
			logger.error('Received {} instead of 200'.format(str(code)))
		elif "error" in resp.json():
			logger.error('Received error response'.format(str(code)))
		else:
			players = resp.json()['result']
			
			for player in players:
				# only one audio or video player can be active at a time, but need to make sure we don't accidentally get a photo player
				if player['type'] in [audio_player_type, video_player_type]:
					playerid = player['playerid']
					the_type = player['type']
					logger.info('Active {} player found with id of {}'.format(the_type, str(playerid)))
					
					return the_type, playerid		
				
		logger.info('No active player found')
		return None	
	
	################## Media Info #######################
	def get_current_media_info(kodi_location):
		player_info = find_active_player(kodi_location)
		
		if player_info is not None:
			player_type, playerid = player_info
			logger.info('Attempting to retrieve info on current item for player with id of {}...'.format(str(playerid)))
			payload = {
				"method": "Player.GetProperties",
				"params": {
					"playerid": playerid,
					"properties": [
						"time",
						"totaltime"
					]
				}
			}
			resp = requests.post(get_url(kodi_location), json=wrap_payload(payload))
			code = resp.status_code
			if code != 200:
				logger.error('Received {} instead of 200'.format(str(code)))
			elif "error" in resp.json():
				logger.error('Received error response'.format(str(code)))
			else:
				result = resp.json()['result']
				t = result['time']
				current_time_seconds = t['seconds'] + t['minutes'] * 60 + t['hours'] * 3600
				t = result['totaltime']
				total_time_seconds = t['seconds'] + t['minutes'] * 60 + t['hours'] * 3600
				logger.info('Current time is {} seconds out of total time of {} seconds'.format(str(current_time_seconds), str(total_time_seconds)))
				return playerid, current_time_seconds, total_time_seconds
		
		return None
	
	################## Player Operations #######################
	def stop_active_player(kodi_location):
		player_info = find_active_player(kodi_location)
		
		if player_info is not None:
			player_type, playerid = player_info
			logger.info('Active {} player found with id of {} so attempting to stop it...'.format(player_type, str(playerid)))
			payload = {
				"method": "Player.Stop",
				"params": {
					"playerid": playerid
				}
			}
			resp = requests.post(get_url(kodi_location), json=wrap_payload(payload))
			code = resp.status_code
			if code != 200:
				logger.error('Received {} instead of 200'.format(str(code)))
			elif "error" in resp.json():
				logger.error('Received error response'.format(str(code)))
			else:
				logger.info('Active {} player with id of {} stopped successfully'.format(player_type, str(playerid)))
		
	def play_pause_active_player(kodi_location):
		player_info = find_active_player(kodi_location)
		
		if player_info is not None:
			player_type, playerid = player_info
			logger.info('Attempting to toggle the play/pause state for {} player with id of {}...'.format(player_type, str(playerid)))
			payload = {
				"method": "Player.PlayPause",
				"params": {
					"playerid": playerid
				}
			}
			resp = requests.post(get_url(kodi_location), json=wrap_payload(payload))
			code = resp.status_code
			if code != 200:
				logger.error('Received {} instead of 200'.format(str(code)))
			elif "error" in resp.json():
				logger.error('Received error response'.format(str(code)))
			else:
				logger.info('{} player with id of {} play/pause state successfully toggled'.format(player_type, str(playerid)))
	
		
	def go_to_within_track(kodi_location, time_hours=0, time_minutes=0, time_seconds=0):
		if time_hours == '':
			time_hours = 0
		if time_minutes == '':
			time_minutes = 0
		if time_seconds == '':
			time_seconds == 0
		time_seconds = int(time_seconds) + 60 * int(time_minutes) + 3600 * int(time_hours)
			
		resp = get_current_media_info(kodi_location)
		if resp is not None:
			player_type, playerid, current_time_seconds, total_time_seconds = resp
			
			if time_seconds < 0:
				time_seconds = 0
			elif time_seconds > total_time_seconds:
				time_seconds = total_time_seconds
				
				
			logger.info('Attempting to change time of current {} player with id of {} to {} seconds...'.format(player_type, str(playerid), str(time_seconds)))
			
			hours = 0
			minutes = 0
			seconds = 0
			
			if time_seconds > 59:
				minutes = int(time_seconds / 60)
				seconds = int(time_seconds) - (minutes * 60)
				
				if minutes > 59:
					hours = int(minutes / 60)
					minutes = minutes - (hours * 60)
			else:
				seconds = time_seconds
			
			payload = {
				"method": "Player.Seek",
				"params": {
					"playerid": playerid,
					"value": {
						"hours": hours,
						"minutes": minutes,
						"seconds": seconds
					}
				}
			}
			logger.info(payload)
			resp = requests.post(get_url(kodi_location), json=wrap_payload(payload))
			code = resp.status_code
			if code != 200:
				logger.error('Received {} instead of 200'.format(str(code)))
			elif "error" in resp.json():
				logger.error('Received error response')
				logger.error(resp.json())
			else:
				logger.info('Successfully changed time of {} player with id of {}'.format(player_type, str(playerid)))
			
		
	def seek_within_track(kodi_location, direction='forward', time_hours=0, time_minutes=0, time_seconds=0):
		if time_hours == '':
			time_hours = 0
		if time_minutes == '':
			time_minutes = 0
		if time_seconds == '':
			time_seconds == 0
		time_seconds = int(time_seconds) + 60 * int(time_minutes) + 3600 * int(time_hours)
		if direction.lower() == 'back':
			time_seconds = -1 * time_seconds
		
		resp = get_current_media_info(kodi_location)
		if resp is not None:
			player_type, playerid, current_time_seconds, total_time_seconds = resp
			logger.info('Attempting to change time for {} player with id of {} by {} seconds...'.format(player_type, str(playerid), str(time_seconds)))
			
			new_time = current_time_seconds + time_seconds
			go_to_within_track(kodi_location, time_seconds=new_time)
			
			
	def next_track(kodi_location):
		hass.services.call('media_player', 'media_next_track', {'entity_id': get_entity(kodi_location)})
		
	def prev_track(kodi_location):
		hass.services.call('media_player', 'media_previous_track', {'entity_id': get_entity(kodi_location)})
	
	################## Manage Playlist #######################
	def clear_playlist(kodi_location, playlist):
		logger.info('Attempting to clear existing playlist with id of {}...'.format(str(playlist)))
		payload = {
			"method": "Playlist.Clear",
			"params": {
				"playlistid": playlist
			}
		}
		resp = requests.post(get_url(kodi_location), json=wrap_payload(payload))
		code = resp.status_code
		if code != 200:
			logger.error('Received {} instead of 200'.format(str(code)))
		elif "error" in resp.json():
			logger.error('Received error response'.format(str(code)))
		else:
			logger.info('Playlist with id of {} cleared successfully'.format(str(playlist)))
			
			
	def add_item_to_playlist(kodi_location, playlist, item):
		logger.info('Adding {} to playlist with id of {}...'.format(item, str(playlist)))
		payload = {
			"method": "Playlist.Add",
			"params": {
				"playlistid": playlist,
				"item": {
					"file": item
				}
			}
		}
		resp = requests.post(get_url(kodi_location), json=wrap_payload(payload))
		code = resp.status_code
		if code != 200:
			logger.error('Received {} instead of 200'.format(str(code)))
		elif "error" in resp.json():
			logger.error('Received error response'.format(str(code)))
		else:
			logger.info('Item added successfully')


	def start_playing_playlist(kodi_location, playlist, shuffle=False):
		logger.info('Attempting to start playing playlist with id of {} in shuffle mode of {}...'.format(str(playlist), str(shuffle)))
		payload = {
			"method": "Player.Open",
			"params": {
				"item": {
					"playlistid": playlist
				},
				"options": {
					"shuffled": shuffle
				}
			}
		}
		resp = requests.post(get_url(kodi_location), json=wrap_payload(payload))
		code = resp.status_code
		if code != 200:
			logger.error('Received {} instead of 200'.format(str(code)))
		elif "error" in resp.json():
			logger.error('Received error response'.format(str(code)))
		else:
			logger.info('Playlist with id of {} is now playing'.format(str(playlist)))
			
	################## Search Libraries #######################
	def search_songs(kodi_location, kodi_song=None, kodi_artist=None, kodi_album=None):
		logger.info('Searching song database with arguments: kodi_song={}, kodi_artist={}, kodi_album={}...'.format(kodi_song, kodi_artist, kodi_album))
		and_list = []
		song_list = []
		if kodi_song is not None:
			d = {
				"field": "title",
				"value": kodi_song,
				"operator": "contains"
			}
			and_list.append(d)
			
		if kodi_artist is not None:
			d = {
				"field": "artist",
				"value": kodi_artist,
				"operator": "contains"
			}
			and_list.append(d)
			
		if kodi_album is not None:
			d = {
				"field": "album",
				"value": kodi_album,
				"operator": "contains"
			}
			and_list.append(d)
	
		# query audio library to find desired songs
		payload = {
			"method": "AudioLibrary.GetSongs",
			"params": {
				"properties": [
					"title",
					"artist",
					"album",
					"file",
					"track"
				],
				"filter": {
					"and": and_list
				}
			}
		}
		resp = requests.post(get_url(kodi_location), json=wrap_payload(payload))
		code = resp.status_code
		
		if code != 200:
			logger.error('Received {} instead of 200'.format(str(code)))
		elif "error" in resp.json():
			logger.error('Received error response'.format(str(code)))
		else:
			# sort the song list to be in correct album order
			try:
				unsorted_songs = resp.json()['result']['songs']
			except KeyError:
				unsorted_songs = []
				
			songs = sorted(unsorted_songs, key=lambda k: k['track'])
			logger.info('Search found {} songs that met criteria.'.format(str(len(songs))))

			for item in songs:
				song_list.append(item['file'])
				
		return song_list
		
	def search_videos(kodi_location, title):
		logger.info('Searching video database with arguments: title={}...'.format(title))
		and_list = []
		video_list = []
	
		d = {
			"field": "title",
			"value": title,
			"operator": "contains"
		}
		and_list.append(d)
			
		# query video library to find desired video
		payload = {
			"method": "VideoLibrary.GetMovies",
			"params": {
				"properties": [
					"title",
					"file"
				],
				"filter": {
					"and": and_list
				}
			}
		}
		resp = requests.post(get_url(kodi_location), json=wrap_payload(payload))
		code = resp.status_code
		
		if code != 200:
			logger.error('Received {} instead of 200'.format(str(code)))
		elif "error" in resp.json():
			logger.error('Received error response'.format(str(code)))
		else:
			# sort the song list to be in correct album order
			try:
				videos = resp.json()['result']['movies']
			except KeyError:
				videos = []
				
			logger.info('Search found {} videos that met criteria.'.format(str(len(videos))))

			for item in videos:
				video_list.append(item['file'])
				
		return video_list

	################################### Intent Handling ####################################
	class GenericIntentHandler(intent.IntentHandler):
		def random_response(self):
			responses = [
				"OK",
				"Sure",
				"If you insist",
				"Done",
				"No worries",
				"I can do that",
				"Leave it to me",
				"Consider it done",
				"As you wish",
				"By your command",
				"Affirmative",
				"Roger",
				"Right away",
				"No Problem",
				"Ten Four"
			]
			
			return random.choice(responses)
		
		def extract_location(self, intent_obj):
			logger.info(intent_obj.slots)
			
			if 'kodi_location' in intent_obj.slots:
				return intent_obj.slots['kodi_location']['value']
			else:
				return intent_obj.platform
			
	class PauseResumeKodiMediaIntent(GenericIntentHandler):
		intent_type = 'PauseResumeKodiMediaIntent'
		
		@asyncio.coroutine
		def async_handle(self, intent_obj):
			kodi_location = self.extract_location(intent_obj)
			play_pause_active_player(kodi_location)
		
			response = intent_obj.create_response()
			response.async_set_speech(self.random_response())
			return response
	
	class StopKodiMediaIntent(GenericIntentHandler):
		intent_type = 'StopKodiMediaIntent'
		
		@asyncio.coroutine
		def async_handle(self, intent_obj):
			kodi_location = self.extract_location(intent_obj)
			stop_active_player(kodi_location)
		
			response = intent_obj.create_response()
			response.async_set_speech(self.random_response())
			return response
			
	class KodiNextTrackIntent(GenericIntentHandler):
		intent_type = 'KodiNextTrackIntent'
		
		@asyncio.coroutine
		def async_handle(self, intent_obj):
			kodi_location = self.extract_location(intent_obj)
			next_track(kodi_location)
		
			response = intent_obj.create_response()
			response.async_set_speech(self.random_response())
			return response
			
	class KodiPrevTrackIntent(GenericIntentHandler):
		intent_type = 'KodiPrevTrackIntent'
		
		@asyncio.coroutine
		def async_handle(self, intent_obj):
			kodi_location = self.extract_location(intent_obj)
			prev_track(kodi_location)
		
			response = intent_obj.create_response()
			response.async_set_speech(self.random_response())
			return response
			
	class KodiGoToTimeIntent(GenericIntentHandler):
		intent_type = 'KodiGoToTimeIntent'
		
		@asyncio.coroutine
		def async_handle(self, intent_obj):
			kodi_location = self.extract_location(intent_obj)
			param_dict = copy(intent_obj.slots)
			try:
				del param_dict['kodi_location']
			except KeyError:
				pass
			go_to_within_track(kodi_location, **param_dict)
		
			response = intent_obj.create_response()
			response.async_set_speech(self.random_response())
			return response
	
	class KodiDeltaTimeIntent(GenericIntentHandler):
		intent_type = 'KodiDeltaTimeIntent'
		
		@asyncio.coroutine
		def async_handle(self, intent_obj):
			kodi_location = self.extract_location(intent_obj)
			param_dict = copy(intent_obj.slots)
			try:
				del param_dict['kodi_location']
			except KeyError:
				pass
			seek_within_track(kodi_location, **param_dict)
		
			response = intent_obj.create_response()
			response.async_set_speech(self.random_response())
			return response
		
	class PlayKodiVideoIntent(GenericIntentHandler):
		intent_type = 'PlayKodiVideoIntent'
		
		@asyncio.coroutine
		def async_handle(self, intent_obj):
			kodi_location = self.extract_location(intent_obj)
			param_dict = copy(intent_obj.slots)
			try:
				del param_dict['kodi_location']
			except KeyError:
				pass
				
			video_list = search_videos(kodi_location, **param_dict)
			if video_list:
				# only continue if we found at least one video
				
				# look for an active player and stop it if it is playing
				stop_active_player(kodi_location)
				
				# get the playlist and clear it
				clear_playlist(kodi_location, video_playlist)

				# we only want one song even if we found multiples so just add the first one to the play list
				add_item_to_playlist(kodi_location, video_playlist, video_list[0])
				
				# start playing the playlist
				start_playing_playlist(kodi_location, video_playlist)
		
			response = intent_obj.create_response()
			response.async_set_speech(self.random_response())
			return response
			
	class PlayKodiSongIntent(GenericIntentHandler):
		intent_type = 'PlayKodiSongIntent'
		
		@asyncio.coroutine
		def async_handle(self, intent_obj):
			kodi_location = self.extract_location(intent_obj)
			param_dict = copy(intent_obj.slots)
			try:
				del param_dict['kodi_location']
			except KeyError:
				pass
				
			try:
				param_dict['kodi_song'] = param_dict['kodi_song']['value']
			except KeyError:
				pass
			
			try:
				param_dict['kodi_artist'] = param_dict['kodi_artist']['value']
			except KeyError:
				pass
				
			try:
				param_dict['kodi_album'] = param_dict['kodi_album']['value']
			except KeyError:
				pass
				
			song_list = search_songs(kodi_location, **param_dict)
			if song_list:
				# only continue if we found at least one song
				
				# look for an active player and stop it if it is playing
				stop_active_player(kodi_location)
				
				# get the playlist and clear it
				clear_playlist(kodi_location, audio_playlist)

				# we only want one song even if we found multiples so just add the first one to the play list
				add_item_to_playlist(kodi_location, audio_playlist, song_list[0])
				
				# start playing the playlist
				start_playing_playlist(kodi_location, audio_playlist)
		
			response = intent_obj.create_response()
			response.async_set_speech(self.random_response())
			return response
			
	class PlayKodiArtistIntent(GenericIntentHandler):
		intent_type = 'PlayKodiArtistIntent'
		
		@asyncio.coroutine
		def async_handle(self, intent_obj):
			kodi_location = self.extract_location(intent_obj)
			param_dict = copy(intent_obj.slots)
			try:
				del param_dict['kodi_location']
			except KeyError:
				pass
				
			try:
				param_dict['kodi_artist'] = param_dict['kodi_artist']['value']
			except KeyError:
				pass
				
			song_list = search_songs(kodi_location, **param_dict)
			if song_list:
				# only continue if we found at least one song
				
				# look for an active audio player and stop it if it is playing
				stop_active_player(kodi_location)
				
				# get the playlist and clear it
				clear_playlist(kodi_location, audio_playlist)

				# add these songs to the playlist
				for song in song_list:
					add_item_to_playlist(kodi_location, audio_playlist, song)
				
				# start playing the playlist
				start_playing_playlist(kodi_location, audio_playlist, shuffle=True)
		
			response = intent_obj.create_response()
			response.async_set_speech(self.random_response())
			return response
			
	class PlayKodiAlbumIntent(GenericIntentHandler):
		intent_type = 'PlayKodiAlbumIntent'
		
		@asyncio.coroutine
		def async_handle(self, intent_obj):
			kodi_location = self.extract_location(intent_obj)
			param_dict = copy(intent_obj.slots)
			try:
				del param_dict['kodi_location']
			except KeyError:
				pass
				
			try:
				param_dict['kodi_artist'] = param_dict['kodi_artist']['value']
			except KeyError:
				pass
				
			try:
				param_dict['kodi_album'] = param_dict['kodi_album']['value']
			except KeyError:
				pass
				
			song_list = search_songs(kodi_location, **param_dict)
			if song_list:
				# only continue if we found at least one song
				
				# look for an active audio player and stop it if it is playing
				stop_active_player(kodi_location)
				
				# get the playlist and clear it
				clear_playlist(kodi_location, audio_playlist)

				# add these songs to the playlist
				for song in song_list:
					add_item_to_playlist(kodi_location, audio_playlist, song)
				
				# start playing the playlist
				start_playing_playlist(kodi_location, audio_playlist)
		
			response = intent_obj.create_response()
			response.async_set_speech(self.random_response())
			return response
			
	intent.async_register(hass, PauseResumeKodiMediaIntent())
	intent.async_register(hass, StopKodiMediaIntent())
	intent.async_register(hass, KodiNextTrackIntent())
	intent.async_register(hass, KodiPrevTrackIntent())
	intent.async_register(hass, KodiGoToTimeIntent())
	intent.async_register(hass, KodiDeltaTimeIntent())
	
	intent.async_register(hass, PlayKodiVideoIntent())
	intent.async_register(hass, PlayKodiSongIntent())
	intent.async_register(hass, PlayKodiArtistIntent())
	intent.async_register(hass, PlayKodiAlbumIntent())
	
	
	return True
	

	
