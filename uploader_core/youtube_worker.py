from PyQt5.QtCore import QObject, pyqtSignal, QRunnable
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

class YouTubeWorkerSignals(QObject):
    finished = pyqtSignal(str)  # Signal emitted when the upload is finished
    progress = pyqtSignal(int)   # Signal emitted to indicate upload progress
    error = pyqtSignal(str)      # Signal emitted when an error occurs

class PlaylistWorkerSignals(QObject):
    finished = pyqtSignal(list)  # Signal emitted when playlist list is retrieved
    error = pyqtSignal(str)      # Signal emitted when an error occurs

class PlaylistWorker(QRunnable):
    """Worker для получения списка плейлистов пользователя"""
    
    def __init__(self, credentials):
        super().__init__()
        self.credentials = credentials
        self.signals = PlaylistWorkerSignals()

    def run(self):
        try:
            # Build the YouTube service
            youtube = build('youtube', 'v3', credentials=self.credentials, cache_discovery=False)
            
            # Get playlists
            playlists = []
            next_page_token = None
            
            while True:
                request = youtube.playlists().list(
                    part='snippet,contentDetails',
                    mine=True,
                    maxResults=50,
                    pageToken=next_page_token
                )
                
                response = request.execute()

                for playlist in response.get('items', []):
                    playlists.append({
                        'id': playlist['id'],
                        'title': playlist['snippet']['title'],
                        'description': playlist['snippet'].get('description', ''),
                        'item_count': playlist['contentDetails'].get('itemCount', 0)
                    })
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
            
            self.signals.finished.emit(playlists)
            
        except HttpError as e:
            self.signals.error.emit(f'Ошибка API YouTube: {e.resp.status} {e.content}')
        except Exception as e:
            self.signals.error.emit(f'Произошла непредвиденная ошибка: {str(e)}')

class YouTubeWorker(QRunnable):
    def __init__(self, credentials, video_path, title, description, tags, privacy_status, category, publish_at, playlist_id=None, made_for_kids=False):
        super().__init__()
        self.credentials = credentials
        self.video_path = video_path
        self.title = title
        self.description = description
        self.tags = tags
        self.privacy_status = privacy_status
        self.category = category
        self.publish_at = publish_at
        self.playlist_id = playlist_id
        self.made_for_kids = made_for_kids
        self.signals = YouTubeWorkerSignals()  # Create an instance of the signals class

    def run(self):
        try:
            # Build the YouTube service
            youtube = build('youtube', 'v3', credentials=self.credentials, cache_discovery=False)

            # Prepare the video metadata
            body = {
                'snippet': {
                    'title': self.title,
                    'description': self.description,
                    'tags': self.tags,
                    'categoryId': self.category
                },
                'status': {
                    'privacyStatus': self.privacy_status,
                    'selfDeclaredMadeForKids': self.made_for_kids
                }
            }

            # Set publish time if privacy status is private
            if self.publish_at and self.privacy_status == 'private':
                body['status']['publishAt'] = self.publish_at

            # Prepare the media file for upload
            media = MediaFileUpload(self.video_path, chunksize=-1, resumable=True)

            # Create the request to upload the video
            request = youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress_percentage = int(status.progress() * 100)
                    self.signals.progress.emit(progress_percentage)  # Emit progress signal

            video_id = response.get('id')
            
            # Add video to playlist if specified
            if self.playlist_id and video_id:
                try:
                    youtube.playlistItems().insert(
                        part='snippet',
                        body={
                            'snippet': {
                                'playlistId': self.playlist_id,
                                'resourceId': {
                                    'kind': 'youtube#video',
                                    'videoId': video_id
                                }
                            }
                        }
                    ).execute()
                except HttpError as e:
                    self.signals.error.emit(f'Ошибка API YouTube \
                        | Видео успешно загружено, но не добавлено в плейлист: {e.resp.status} {e.content}')
                except Exception as e:
                    self.signals.error.emit(f'Произошла непредвиденная ошибка \
                        | Видео успешно загружено, но не добавлено в плейлист: {str(e)}')

            # Emit finished signal with the video ID
            self.signals.finished.emit(video_id)

        except HttpError as e:
            self.signals.error.emit(f'Ошибка API YouTube: {e.resp.status} {e.content}')
        except Exception as e:
            self.signals.error.emit(f'Произошла непредвиденная ошибка: {str(e)}')
