#!/usr/bin/env python
'''
Initial idea from public python test code from github.com
https://gist.github.com/sotelo/be57571a1d582d44f3896710b56bc60d ; remove_silence.py
https://github.com/brglng/diff-wave.py

Fred is working on this script.
Tested in python v2.7.15+ will be compatible with 3.4.x later
'''


import sys
import wave
import struct
import time
import shutil
import itertools

#pydub for remove silence
from pydub import AudioSegment

S10_ms = 10000 #10 second = 10 x 1000ms

## --------------------------------------
def detect_leading_silence(sound, silence_threshold=-50.0, chunk_size=10):
    '''
    Fred: TODO: for better alignment, consider to change to 5ms window

    sound is a pydub.AudioSegment
    silence_threshold in dB
    chunk_size in ms

    iterate over chunks until you find the first one with sound
    '''
    trim_ms = 0  # ms
    end_ms = len(sound) - 1000
    while (sound[trim_ms:trim_ms+chunk_size].dBFS < silence_threshold) and (trim_ms<end_ms):
        trim_ms += chunk_size

    return trim_ms

#remove_silence : infile should have more than 10 seoncd of data
def remove_silence(infile):
    #backup file to .org
    shutil.copyfile(infile, infile+".org")

    sound = AudioSegment.from_file(infile, format="wav")    

    start_trim = detect_leading_silence(sound)
    #end_trim = detect_leading_silence(sound.reverse())

    duration = len(sound)
    #Fred:make sure we have enought data of 10 second
    if duration - start_trim < S10_ms:
        start_trim = duration - S10_ms
    
    trimmed_sound = sound[start_trim:duration]
    trimmed_sound.export(infile, format="wav")


## --------------------------------------
def unpack_pcm(packed_values, sampwidth):
    if sampwidth == 2:
        return struct.unpack(str(len(packed_values)/sampwidth) + 'h', packed_values)
    elif sampwidth == 3:
        tmp = struct.unpack(str(len(packed_values)) + 'B', packed_values)
        tmp = [x + (y<<8) + (z<<16) for x,y,z in itertools.izip(*[iter(tmp)]*3)]
        return [x if (x & 0x800000) == 0 else x - (1<<24) for x in tmp]

def pack_pcm(values, sampwidth):
    if sampwidth == 2:
        pack_len = len(values)
        return struct.pack(str(len(values)) + 'h', *values)
    elif sampwidth == 3:
        tmp = [k for j in itertools.imap(lambda i: (i & 0xff, (i>>8) & 0xff, (i>>16) & 0xff), values) for k in j]
        return struct.pack(str(len(values)*sampwidth) + 'B', *tmp)

def main(argv):
    if len(argv) < 4:
        print("Error: Incorrect arguments")
        print("Usage:")
        print("\tdiff-wave.py input1.wav input2.wav out_diff.wav")
        return 1

    #short_max = sys.maxint   #SHRT_MAX is not defined

    inname1 = argv[1]
    inname2 = argv[2]
    outname = argv[3]

    # 1. remove initial silence to match two input files
    remove_silence(inname1)
    remove_silence(inname2)

    #2. open files for compare
    in1 = wave.open(inname1, 'r')
    in2 = wave.open(inname2, 'r')

    param1 = in1.getparams()
    param2 = in2.getparams()

    #print param1
    #channel, BytePerSample, sampling rate, number of samples , 'NONE', 'not compressed'
    #(2, 2, 48000, 758219, 'NONE', 'not compressed')
    #print param2
    #Fred: number of samples dfference should not block here
    if ( (param1[0] != param2[0]) or 
         (param1[1] != param2[1]) or
         (param1[2] != param2[2]) ):
        print("Input files parameters differ.")
        print("param1 = ", param1)
        print("param1 = ", param2)
        return 2

    if ( (param1[3]<480000) or (param2[3]<480000) ):
        print("Input files length is not enough.")
        print("param1 number of samples", param1[3])
        print("param2 number of samples", param2[3])
        return 3

    starttime = time.time()
    #print(starttime)

    #2.1 compare only 10 second. if input file had only silence, this cause problem
    packed_values1 = in1.readframes(param1[2]*10)
    packed_values2 = in2.readframes(param2[2]*10)
    #packed_values1 = in1.readframes(param1[3])
    #packed_values2 = in2.readframes(param1[3])

    values1 = unpack_pcm(packed_values1, param1[1])
    values2 = unpack_pcm(packed_values2, param2[1])
    
    len1 = len(values1)
    len2 = len(values2)
    
    #3. Normalized PCMs before the comparison
    #TODO: Fred to implement normalization


    #4. DIFF samples
    #Fred: how to calculate % of diff
    outvalues = list( itertools.imap(lambda x,y: x - y, values1, values2) )
    packed_outvalues = pack_pcm(outvalues, param1[1])
    
    #5. save output file for further analysis
    # RIFF header is 44 byte
    # 48000Hz for 10 second 16 bitspersample 2 channel. 48000 * 2 * 2 * 10 = 1920000
    # total file size = 1920044
    out = wave.open(outname, 'w')
    out.setparams(param1)
    out.writeframesraw(packed_outvalues)
    out.close()

    #6. Analyze output file with PyDub
    audio_diff = AudioSegment.from_file(outname)
    db = audio_diff.max_dBFS  # RETURNS A NEGATIVE DB VALUE FROM MAX PEAK
    rms = audio_diff.rms  # RETURNS LOUDNESS LEVEL BUT NOT IN dB
    dbfs = audio_diff.dBFS

    print('max peak value', db)
    print('RMS value return from pydub', rms, '...not sure how to interpret this')
    print('dBFS value', dbfs)

    endtime = time.time()
    print("Elapsed time: ", endtime - starttime)

    in1.close()
    in2.close()

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
