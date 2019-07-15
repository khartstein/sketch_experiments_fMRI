#!/usr/bin/env python

# Run this from the command line from 'sketch-morph/fMRI/exp_2' directory using:
#   python sketchID_presentation_fmri.py

# Optionally supply DBIC ID, accession number, and participant number:
#   python actions_presentation.py <DBIC ID> <accession number> <participant_number> <run_number>
# Command line arguments must be in order!

# TODO:

import sys
import time
import serial
import pandas as pd
import numpy as np
from os import makedirs
from os.path import join, exists, abspath, dirname
from psychopy import visual, core, event, gui, logging, sound
from psychopy.constants import (NOT_STARTED, STARTED, PLAYING, PAUSED,
                                STOPPED, FINISHED, PRESSED, RELEASED, FOREVER)

# Set up GUI for inputing participant/run information (with defaults)
if len(sys.argv) > 1:
    DBIC_ID = sys.argv[1]
    accession = sys.argv[2]
    participant = sys.argv[3]
    run = sys.argv[4]
else:
    #DBIC_ID = "e.g., SID000001"
    #accession = "e.g., A000001"
    #participant = "e.g., 1"
    DBIC_ID = "SID000001"
    accession = "A000000"
    participant = "00"
    run = "00"

run_configuration = gui.Dlg(title='Run configuration')
run_configuration.addField("DBIC ID:", DBIC_ID)
run_configuration.addField("Scan accession number:", accession)
run_configuration.addField("Participant:", participant)
run_configuration.addField("Run number:", run)
run_configuration.show()

if run_configuration.OK:
    DBIC_ID = run_configuration.data[0]
    accession = run_configuration.data[1]
    participant = str(run_configuration.data[2])
    run = int(run_configuration.data[3])
elif not run_configuration.OK:
    core.quit()

# Start PsychoPy's clock (mostly for logging)
run_clock = core.Clock()

# Add a new logging level name called bids
# we will use this level to log information that will be saved
# in the _events.tsv file for this run
BIDS = 26
logging.addLevel(BIDS, 'BIDS')

def logbids(msg, t=None, obj=None):
    """logbids(message)
    logs a BIDS related message
    """
    logging.root.log(msg, level=BIDS, t=t, obj=obj)

# BIDS TEMPLATE
logbids("onset\tduration\tstim_type\tstim_fn")
template_bids = '{onset:.3f}\t{duration:.3f}\t{stim_type}\t{stim_fn}'

# Set up all the relevant directories here
HERE = abspath(dirname(__file__))
STIMDIR = join(HERE, "stim")
CSVDIR = join(HERE, "runs")
RESDIR = join(HERE, "res")
if not exists(RESDIR):
    makedirs(RESDIR)

# Set up PsychoPy's logging function
logging.setDefaultClock(run_clock)
log = logging.LogFile(f=join("res", 'log_p{:02d}_r{:02d}.txt'.format(
                int(participant), int(run))), level=logging.INFO,
                filemode='w')

# Load in events / trial order
trials_file = join(CSVDIR,'Sub{:02d}_Run{:02d}.csv'.format(
                         int(participant), int(run)))
trials = pd.read_csv(trials_file)
assert trials.shape[0] == 72

# Open window and wait for first scanner trigger

# for scanner projector
win = visual.Window([1280,960], screen=0, fullscr=True, color=(128,128,128),
                    colorSpace='rgb255', name='Window')

# # for testing
# win = visual.Window([1680,1050], screen=0, fullscr=True, color=(128,128,128),
#                     colorSpace='rgb255', name='Window')

# # fixation crosses
# fixation = visual.TextStim(win, pos=(0, 0), text="+", name="Fixation",
#                            color=(0,255,0), colorSpace='rgb255', height=0.07)
# fixation_dark = visual.TextStim(win, pos=(0, 0), text="+", name="Fixation_Dark",
#                                 color=(0,128,0), colorSpace='rgb255', height = 0.07)

# concentric circles for fixation
fixation_fn = join(HERE, 'fixation_green_thumb.png')
fixation = visual.ImageStim(win, fixation_fn, name='Fixation', colorSpace='rgb', autoLog=True)

# load stimuli
stimuli = {}
durations = []
trial_jitters = []
onsets = []
where_correct = []
load_text = "Loading stimuli..."
load_disp = visual.TextStim(win, text=load_text,
                               alignHoriz='center', alignVert='center',
                               name='Loading', color='black')
load_disp.draw()
win.flip()

for trial in range(trials.shape[0]):
    trial_obj = trials.loc[trial,'ObjectID']    # object category
    stim_number = trials.loc[trial,'StimNo']    # which exemplar
    stim_type = trials.loc[trial,'StimType']    # ['sketch','fixation','instructions','question']
    onsets.append(trials.loc[trial,'Onset'])
    durations.append(trials.loc[trial,'Duration'])
    trial_jitters.append(trials.loc[trial,'Jitter'])
    print("Loading {0}".format(trial_obj))
    if stim_type == 'fixation':
        stimuli[trial] = fixation
    elif stim_type == 'question':
        # load question
        names = trial_obj.split('_')
        animate_name = names[0]
        inanimate_name = names[1]
        whereanimate = trials.loc[trial,'WhereAnimate']
        if whereanimate == "right":
            right_text = animate_name
            left_text = inanimate_name
        else:
            right_text = inanimate_name
            left_text = animate_name

        center_text = 'neither'
        question_text = 'What object identity did you see?'
        probe_left = visual.TextStim(win, text=left_text, pos=(-.3, 0),
                                     alignHoriz='center', alignVert='center',
                                     name='Left probe', color ='black')
        probe_right = visual.TextStim(win, text=right_text, pos=(.3, 0),
                                      alignHoriz='center', alignVert='center',
                                      name='Right probe', color='black')
        probe_center = visual.TextStim(win, text=center_text, pos=(0,-.3),
                                      alignHoriz='center', alignVert='center',
                                      name='Bottom probe', color='black')
        question = visual.TextStim(win, text=question_text, pos=(0, .4), alignHoriz='center',
                           alignVert='bottom', wrapWidth=2, color='black', name='What object?')
        stimuli[trial] = [probe_left, probe_right, probe_center, question]
    elif stim_type == 'sketch':
        # load the sketch video
        clip_fn = join(STIMDIR, trial_obj+'_'+str(stim_number)+'_8s.mov')
        stimuli[trial] = visual.MovieStim3(win, clip_fn,
                                    pos=(0, 0), flipVert=False,
                                    flipHoriz=False, loop=False,
                                    noAudio=True, name=trial_obj)
    else:
        print('unknown stimulus type...')
        print(stim_type)
        win.close()
        core.quit()

instructions = visual.TextStim(win, wrapWidth=1.8,
                alignHoriz='center', alignVert='center', name='Instructions',
                text=("Please observe the following sketches of objects. \n\n"
                      "Press any button as soon as you recognize the object's identity\n\n"
                      "After each trial, you will indicate what you saw."),
                color='black')
                # pos=[-.9, .6]

instructions.draw()
win.flip()

instructions_wait = True
while instructions_wait:
    keys = event.getKeys()
    if 'space' in keys or 'return' in keys:
        logging.info("Finished instructions")
        instructions_wait = False
    if 'q' in keys or 'escape' in keys:
        quitting = ('Quit command ("q" or "escape") was detected! '
                    'Quitting experiment')
        logging.info(quitting)
        print(quitting)
        win.close()
        core.quit()

waiting = visual.TextStim(win, pos=[0, 0], text="Waiting for scanner...",
                          color='black', name="Waiting")
waiting_fake = visual.TextStim(win, pos=[0, 0], text="Waiting for (fake) scanner...",
                               color='black', name="Waiting_fake")

win.mouseVisible = False

serial_path = '/dev/cu.USA19H62P1.1'
# serial_path = '/dev/cu.USA19H142P1.1'
# serial_path = '/dev/tty.USA19H142P1.1'

if not exists(serial_path):
    waiting_fake.draw()
    win.flip()
    serial_exists = False
    b_serial = "No serial device detected, using keyboard"
    event.waitKeys(keyList=['5'])

    first_trigger = "Got sync from keyboard. Resetting clocks"
else:
    waiting.draw()
    win.flip()
    serial_exists = True
    b_serial = "Serial device detected"
    ser = serial.Serial(serial_path, 19200, timeout=.0001)
    ser.flushInput()
    scanner_wait = True

    while scanner_wait:
        ser_out = ser.read()
        if b'5' in ser_out:
            scanner_wait = False
            first_trigger = "Got sync from scannner! Resetting clocks"

# Set run start time and reset PsychoPy's core.Clock() on first trigger
run_clock.reset()
run_start = time.time()
timer_exp = core.Clock()

logging.info(b_serial)
logging.info(first_trigger)
print(first_trigger)
print(b_serial)
bRepeat = 0

# Start fixation after scanner trigger
fixation.draw()
win.flip()

# Start looping through trials
# for trial in range(20):
for trial in range(trials.shape[0]):
    # prepare stimulus for this trial
    stim_type = trials.loc[trial,'StimType']
    trial_obj = trials.loc[trial,'ObjectID']
    stimulus = stimuli[trial]

    print("stimulus prepared")

    if serial_exists:
        ser.flushInput()

    core.wait(onsets[trial] - (time.time()-run_start), hogCPUperiod=0.2)

    stim_start = time.time()
    if stim_type == 'fixation':
        win.logOnFlip(level=logging.EXP, msg='fixation trial start')
        stimulus.draw()
        win.flip()

        now = time.time()
        while now-stim_start <= durations[trial]:
            stimulus.draw()
            win.flip()

            if serial_exists:
                key = str(ser.read())
            else:
                key = event.getKeys(['1','2','3','4','5'])

            if '1' in list(key):
                which_key = '1'
            elif '2' in list(key):
                which_key = '2'
            elif '3' in list(key):
                which_key = '3'
            elif '4' in list(key):
                which_key = '4'
            elif '5' in list(key):
                which_key = 'scanner_trigger'
                logging.info(which_key)
            else:
                which_key = False

            if which_key in ['1','2','3','4']:
                logbids(template_bids.format(
                    onset=time.time()-run_start,
                    duration=0.,
                    stim_type='button_press',
                    stim_fn=which_key)
                    )
            now = time.time()
    elif stim_type == 'question':
        now = time.time()
        # display question
        stimulus[0].draw()
        stimulus[1].draw()
        stimulus[2].draw()
        stimulus[3].draw()
        win.flip()

        while now-stim_start <= durations[trial]:
            if serial_exists:
                key = str(ser.read())
            else:
                key = event.getKeys(['1','2','3','4','5'])

            if '1' in list(key):
                which_key = '1'
            elif '2' in list(key):
                which_key = '2'
            elif '3' in list(key):
                which_key = '3'
            elif '4' in list(key):
                which_key = '4'
            elif '5' in list(key):
                which_key = 'scanner_trigger'
                logging.info(which_key)
            else:
                which_key = False

            if which_key in ['1','2','3','4']:
                logbids(template_bids.format(
                    onset=time.time()-run_start,
                    duration=0.,
                    stim_type='button_press',
                    stim_fn=which_key)
                    )
            now = time.time()
    else:
        # show the sketch
        now = time.time()
        while stimulus.status != visual.FINISHED:
            stimulus.draw()
            fixation.draw()

            if serial_exists:
                key = str(ser.read())
            else:
                key = event.getKeys(['1','2','3','4','5'])

            if '1' in list(key):
                which_key = '1'
            elif '2' in list(key):
                which_key = '2'
            elif '3' in list(key):
                which_key = '3'
            elif '4' in list(key):
                which_key = '4'
            elif '5' in list(key):
                which_key = 'scanner_trigger'
                logging.info(which_key)
            else:
                which_key = False

            if which_key in ['1','2','3','4']:
                logbids(template_bids.format(
                    onset=time.time()-run_start,
                    duration=0.,
                    stim_type='button_press',
                    stim_fn=which_key)
                    )
            now = time.time()
            win.flip()

    fixation.draw()
    win.flip()
    fix_start = time.time()

    print("Stimulus {0} was on for {1}".format(trial_obj+'_'+stim_type,fix_start-stim_start))


    # log the trial
    logbids(template_bids.format(
            onset=stim_start-run_start,
            duration=time.time()-stim_start,
            stim_type=stim_type,
            stim_fn=trial_obj)
        )

    # while time.time()-stim_start <=durations[trial]+2-trial_jitters[trial]:
    #     fixation.draw()
    #     win.flip()

    print("Fixation was on screen for {0}".format(time.time()-fix_start))

    if serial_exists:
        key = str(ser.read())
    else:
        key = event.getKeys(['1','2','3','4','5'])

    if '1' in list(key):
        which_key = '1'
    elif '2' in list(key):
        which_key = '2'
    elif '3' in list(key):
        which_key = '3'
    elif '4' in list(key):
        which_key = '4'
    elif '5' in list(key):
        which_key = 'scanner_trigger'
        logging.info(which_key)
    else:
        which_key = False

    if which_key in ['1','2','3','4']:
        logbids(template_bids.format(
            onset=time.time()-run_start,
            duration=0.,
            stim_type='button_press',
            stim_fn=which_key)
            )

core.wait(6, hogCPUperiod=0.1)

finished = "Finished run successfully!"
logging.info(finished)
print(finished)
win.close()
core.quit()
