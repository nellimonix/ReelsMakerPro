from PyQt5.QtCore import QObject, pyqtSignal, QRunnable
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

class YouTubeWorkerSignals(QObject):
    finished = pyqtSignal(str)  # Signal emitted when the upload is finished
    progress = pyqtSignal(int)   # Signal emitted to indicate upload progress
    error = pyqtSignal(str)      # Signal emitted when an error occurs

class YouTubeWorker(QRunnable):
    def __init__(self, credentials, video_path, title, description, tags, privacy_status, category, publish_at):
        super().__init__()
        self.credentials = credentials
        self.video_path = video_path
        self.title = title
        self.description = description
        self.tags = tags
        self.privacy_status = privacy_status
        self.category = category
        self.publish_at = publish_at
        self.signals = YouTubeWorkerSignals()  # Create an instance of the signals class

    def run(self):
        try:
            # Build the YouTube service
            youtube = build('youtube', 'v3', credentials=self.credentials)

            # Prepare the video metadata
            body = {
                'snippet': {
                    'title': self.title,
                    'description': self.description,
                    'tags': self.tags,
                    'categoryId': self.category
                },
                'status': {
                    'privacyStatus': self.privacy_status
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

            # Emit finished signal with the video ID
            self.signals.finished.emit(response.get('id'))

        except HttpError as e:
            self.signals.error.emit(f'Ошибка API YouTube: {e.resp.status} {e.content}')
        except Exception as e:
            self.signals.error.emit(f'Произошла непредвиденная ошибка: {str(e)}')
