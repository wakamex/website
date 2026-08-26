# I made Youtube CLI Uploader

I looked around for a package to automate publishing videos to youtube, to help me automate my AI generated recaps of the DARPA Heavy Challenge ([example](https://www.youtube.com/watch?v=YXg4ovjHfvY)).

So I made one. [Youtube CLI Uploader](https://github.com/wakamex/youtube-cli-uploader/) lets you upload a video, assign thumbnail and captions, and delete it. Until my app is verified by Google, it can't make the video public. But you can review the private upload and easily flip it to public yourself.

{{ asciinema("/youtube-cli-uploader-demo.cast") }}

The package is public now, but each user needs to create a Google Cloud project, enable the YouTube Data API, and supply their own OAuth client.
