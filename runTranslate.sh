#!/bin/bash
set -euo pipefail

export GOOGLE_APPLICATION_CREDENTIALS=~/googleSpeech/sound.json
#python transcribe_async.py gs://audio-transcripts-regional/external.flac > external.txt
rm -rf tmpOut
mkdir tmpOut

if [ "$#" -eq 1 ]; then
	ffmpeg -i $1 -filter_complex "pan=mono|c0=c0+c1[aout]" -map "[aout]" -f segment -segment_time 600 tmpOut/mono%03d.flac
	
elif [ "$#" -eq 2 ]; then
	ffmpeg -i $1 -i $2 -filter_complex "[0:a][1:a]amerge=inputs=2,pan=mono|c0=c0+c1+c2+c3[aout]" -map "[aout]" -f segment -segment_time 600 tmpOut/mono%03d.flac
else
	echo "Help!? Wrong number of arguments"
	exit 1
fi


for file in tmpOut/*.flac; do
	python transcribe_async.py $file
done

echo -e "Transcription\tCertainty" > transcription.tsv

for file in tmpOut/*.tsv; do
	cat $file >> transcription.tsv
done


#	python transcribe_async.py mono.flac