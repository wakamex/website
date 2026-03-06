#!/bin/bash
files="${@:-index.html style.css resume.html}"
gcloud compute scp $files mc-new:~ --zone=us-central1-a
for f in $files; do
    gcloud compute ssh mc-new --zone=us-central1-a --command="sudo mv ~/${f##*/} /var/www/mihaicosma.com/"
done
