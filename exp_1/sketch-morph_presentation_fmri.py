#!/usr/bin/env python

# Run this from the command line from 'sketch-morph' directory using:
#   python sketch-morph_presentation_fmri_streamlined.py

# Optionally supply DBIC ID, accession number, and participant number:
#   python actions_presentation.py <DBIC ID> <accession number> <participant_number> <run_number>
# Command line arguments must be in order!

# TODO: localizer

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
logbids("onset\tduration\tstim_type\tstim_fn\trepetition")
template_bids = '{onset:.3f}\t{duration:.3f}\t{stim_type}\t{stim_fn}\t' \
                    '{repeat}'

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
assert trials.shape[0] == 48

# Open window and wait for first scanner trigger

# # for scanner projector
# win = visual.Window([1280,960], screen=0, fullscr=True, color=(128,128,128),
#                     colorSpace='rgb255', name='Window')

# for testing
win = visual.Window([1680,1050], screen=0, fullscr=True, color=(128,128,128),
                    colorSpace='rgb255', name='Window')

# # fixation crosses
# fixation = visual.TextStim(win, pos=(0, 0), text="+", name="Fixation",
#                            color=(0,255,0), colorSpace='rgb255', height=0.07)
# fixation_dark = visual.TextStim(win, pos=(0, 0), text="+", name="Fixation_Dark",
#                                 color=(0,128,0), colorSpace='rgb255', height = 0.07)

# concentric circles for fixation
fixation_fn = join(HERE, 'fixation_green_thumb.png')
fixation = visual.ImageStim(win, fixation_fn, name='Fixation', colorSpace='rgb', autoLog=True)
fixation_dark_fn = join(HERE, 'fixation_green_dark_thumb.png')
fixation_dark = visual.ImageStim(win, fixation_dark_fn, name='Fixation_dark', colorSpace='rgb', autoLog=True)

# load stimuli
stimuli = {}
repeats = []
durations = []
trial_jitters = []
onsets = []
fixation_change = []
load_text = "Loading stimuli..."
load_disp = visual.TextStim(win, text=load_text,
                               alignHoriz='center', alignVert='center',
                               name='Loading', color='black')
load_disp.draw()
win.flip()

for trial in range(trials.shape[0]):
    trial_obj = trials.loc[trial,'ObjectID']    # object category
    stim_number = trials.loc[trial,'StimNo']    # which exemplar
    stim_type = trials.loc[trial,'StimType']    # 'sketch' or 'photo'
    repeat = trials.loc[trial,'Repeat']         # is this a repeat of last trial
    repeats.append(repeat)
    onsets.append(trials.loc[trial,'Onset'])
    durations.append(trials.loc[trial,'Duration'])
    trial_jitters.append(trials.loc[trial,'Jitter'])
    fixation_change.append(trials.loc[trial,'FixChange'])
    print("Loading {0}".format(trial_obj))
    if stim_type == 'fixation':
        stimuli[trial] = fixation
    elif stim_type == 'photo':
        # load the photographic image
        img_fn = join(STIMDIR, trial_obj+'_'+str(stim_number)+'.png')
        stimuli[trial] = visual.ImageStim(win, img_fn, name=trial_obj,
                                    autoLog=True)
    elif stim_type == 'sketch':
        # load the sketch video
        clip_fn = join(STIMDIR, trial_obj+'_'+str(stim_number)+'_6s.mov')
        stimuli[trial] = visual.MovieStim3(win, clip_fn,
                                    pos=(0, 0), flipVert=False,
                                    flipHoriz=False, loop=False,
                                    noAudio=True, name=trial_obj)
    else:
        print('unknown stimulus type...')
        win.close()
        core.quit()

instructions = visual.TextStim(win, pos=[-.9, .6], wrapWidth=1.8,
                alignHoriz='left', alignVert='top', name='Instructions',
                text=("Please observe the following objects. \n\n"
                      "When an object appears twice in a row, press "
                      "the yellow button. \n"
                      "When the fixation dot dims, press the blue button."),
                color='black')

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
for trial in range(trials.shape[0]):
    # prepare stimulus for this trial
    stim_type = trials.loc[trial,'StimType']
    trial_obj = trials.loc[trial,'ObjectID']
    stimulus = stimuli[trial]

    if repeats[trial]:
        bRepeat = 1
    else:
        bRepeat = 0

    print("stimulus prepared")

    if serial_exists:
        ser.flushInput()

    core.wait(onsets[trial] - (time.time()-run_start), hogCPUperiod=0.2)

    stim_start = time.time()
    if stim_type == 'fixation':
        win.logOnFlip(level=logging.EXP, msg='fixation trial start')
        stimulus.draw()
        win.flip()
        if fixation_change[trial] == 1:
            time_fix_change = .5+5*(np.random.uniform(low=0.,high=1.,size=1))
            logging.exp('time of fixation change is {0}'.format(time_fix_change))

        fix_wait = True
        now = time.time()
        while now-stim_start <= durations[trial]:
            if fixation_change[trial] == 0 or now-stim_start < time_fix_change:
                stimulus.draw()
            elif now-(stim_start+time_fix_change) > 0.3:
                stimulus.draw()
            elif fix_wait:
                fixation_dark.draw()
                win.logOnFlip('fixation change onset', level=logging.EXP)
                fix_wait = False
            else:
                fixation_dark.draw()
            now = time.time()
            win.flip()

            if serial_exists:
                key = str(ser.read())
            else:
                key = event.getKeys(['1','2','5'])

            if '1' in list(key):
                which_key = '1'
            elif '2' in list(key):
                which_key = '2'
            elif '5' in list(key):
                which_key = 'scanner_trigger'
                logging.info(which_key)
            else:
                which_key = False

            if which_key in ['1','2']:
                logbids(template_bids.format(
                    onset=time.time()-run_start,
                    duration=0.,
                    stim_type='button_press',
                    stim_fn=which_key,
                    repeat='')
                    )

    elif stim_type == 'photo':
        # first presentation
        win.logOnFlip('{0} onset 1'.format(trial_obj), level=logging.EXP)
        stimulus.draw()
        fixation.draw()
        core.wait(0.5-(time.time()-stim_start), hogCPUperiod=0.1)
        win.flip()
        stimulus.draw()
        if fixation_change[trial] == 1:
            time_fix_change = 1.0+4.5*(np.random.uniform(low=0.,high=1.,size=1))
            logging.exp('time of fixation change is {0}'.format(time_fix_change))

        if fixation_change[trial] == 1 and (time_fix_change < 1.7):
            # dim fixation onset AND OFFSET during this presentation
            fixation.draw()
            win.flip()
            stimulus.draw()
            fixation_dark.draw()
            win.logOnFlip('fixation change onset', level=logging.EXP)
            core.wait(time_fix_change-(time.time()-stim_start), hogCPUperiod=0.1)

            win.flip()
            stimulus.draw()
            fixation.draw()
            core.wait(time_fix_change+.3-(time.time()-stim_start), hogCPUperiod=0.1)
            win.flip()
            stimulus.pos = [0,0] + .01*(np.random.randint(low=-3, high=3, size=2))
            fixation.draw()

            while time.time() - stim_start < 2.0:
                if serial_exists:
                    key = str(ser.read())
                else:
                    key = event.getKeys(['1','2','5'])

                if '1' in list(key):
                    which_key = '1'
                elif '2' in list(key):
                    which_key = '2'
                elif '5' in list(key):
                    which_key = 'scanner_trigger'
                    logging.info(which_key)
                else:
                    which_key = False

                if which_key in ['1','2']:
                    logbids(template_bids.format(
                        onset=time.time()-run_start,
                        duration=0.,
                        stim_type='button_press',
                        stim_fn=which_key,
                        repeat='')
                        )
            # core.wait(2.0-(time.time()-stim_start), hogCPUperiod=0.1)

        elif fixation_change[trial] == 1 and (1.7 <= time_fix_change < 2.0):
            # dim fixation onset, extends into blank
            fixation.draw()
            win.flip()
            stimulus.draw()
            fixation_dark.draw()
            win.logOnFlip('fixation change onset', level=logging.EXP)
            core.wait(time_fix_change-(time.time()-stim_start), hogCPUperiod=0.1)
            win.flip()
            stimulus.pos = [0,0] + .01*(np.random.randint(low=-3, high=3, size=2))
            fixation_dark.draw()

            if serial_exists:
                key = str(ser.read())
            else:
                key = event.getKeys(['1','2','5'])

            if '1' in list(key):
                which_key = '1'
            elif '2' in list(key):
                which_key = '2'
            elif '5' in list(key):
                which_key = 'scanner_trigger'
                logging.info(which_key)
            else:
                which_key = False

            if which_key in ['1','2']:
                logbids(template_bids.format(
                    onset=time.time()-run_start,
                    duration=0.,
                    stim_type='button_press',
                    stim_fn=which_key,
                    repeat='')
                    )

        else:
            # fixation does not dim in this section
            fixation.draw()
            win.flip()
            stimulus.pos = [0,0] + .01*(np.random.randint(low=-3, high=3, size=2))
            fixation.draw()
            while time.time() - stim_start < 2.0:
                if serial_exists:
                    key = str(ser.read())
                else:
                    key = event.getKeys(['1','2','5'])

                if '1' in list(key):
                    which_key = '1'
                elif '2' in list(key):
                    which_key = '2'
                elif '5' in list(key):
                    which_key = 'scanner_trigger'
                    logging.info(which_key)
                else:
                    which_key = False

                if which_key in ['1','2']:
                    logbids(template_bids.format(
                        onset=time.time()-run_start,
                        duration=0.,
                        stim_type='button_press',
                        stim_fn=which_key,
                        repeat='')
                        )

            # core.wait(2.0-(time.time()-stim_start), hogCPUperiod=0.1)

        # first blank
        win.flip()
        if fixation_change[trial] == 1 and (1.7 < time_fix_change < 2.0):
            # finish dim fixation period, then draw regular
            fixation.draw()
            core.wait(time_fix_change+.3-(time.time()-stim_start), hogCPUperiod=0.1)
            win.flip()
            stimulus.draw()
            fixation.draw()
            win.logOnFlip('{0} onset 2'.format(trial_obj),level=logging.EXP)

            while time.time()-stim_start < 2.5:
                if serial_exists:
                    key = str(ser.read())
                else:
                    key = event.getKeys(['1','2','5'])

                if '1' in list(key):
                    which_key = '1'
                elif '2' in list(key):
                    which_key = '2'
                elif '5' in list(key):
                    which_key = 'scanner_trigger'
                    logging.info(which_key)
                else:
                    which_key = False

                if which_key in ['1','2']:
                    logbids(template_bids.format(
                        onset=time.time()-run_start,
                        duration=0.,
                        stim_type='button_press',
                        stim_fn=which_key,
                        repeat='')
                        )

            # core.wait(2.5-(time.time()-stim_start), hogCPUperiod=0.1)
        elif fixation_change[trial] == 1 and (2.0 <= time_fix_change < 2.2):
            # fixation dim happens all during the blank
            fixation_dark.draw()
            win.logOnFlip('fixation change onset', level=logging.EXP)
            core.wait(time_fix_change-(time.time()-stim_start), hogCPUperiod=0.1)
            win.flip()
            fixation.draw()
            while time.time()-stim_start < time_fix_change+.3:
                if serial_exists:
                    key = str(ser.read())
                else:
                    key = event.getKeys(['1','2','5'])

                if '1' in list(key):
                    which_key = '1'
                elif '2' in list(key):
                    which_key = '2'
                elif '5' in list(key):
                    which_key = 'scanner_trigger'
                    logging.info(which_key)
                else:
                    which_key = False

                if which_key in ['1','2']:
                    logbids(template_bids.format(
                        onset=time.time()-run_start,
                        duration=0.,
                        stim_type='button_press',
                        stim_fn=which_key,
                        repeat='')
                        )
            # core.wait(time_fix_change+.3-(time.time()-stim_start), hogCPUperiod=0.1)
            win.flip()
            stimulus.draw()
            fixation.draw()
            while time.time()-stim_start < 2.5:
                if serial_exists:
                    key = str(ser.read())
                else:
                    key = event.getKeys(['1','2','5'])

                if '1' in list(key):
                    which_key = '1'
                elif '2' in list(key):
                    which_key = '2'
                elif '5' in list(key):
                    which_key = 'scanner_trigger'
                    logging.info(which_key)
                else:
                    which_key = False

                if which_key in ['1','2']:
                    logbids(template_bids.format(
                        onset=time.time()-run_start,
                        duration=0.,
                        stim_type='button_press',
                        stim_fn=which_key,
                        repeat='')
                        )
            # core.wait(2.5-(time.time()-stim_start), hogCPUperiod=0.1)
        elif fixation_change[trial] == 1 and (2.2 <= time_fix_change < 2.5):
            # fixation dims during the blank, extends into next presentation
            fixation_dark.draw()
            win.logOnFlip('fixation change onset', level=logging.EXP)
            while time.time()-stim_start < time_fix_change:
                if serial_exists:
                    key = str(ser.read())
                else:
                    key = event.getKeys(['1','2','5'])

                if '1' in list(key):
                    which_key = '1'
                elif '2' in list(key):
                    which_key = '2'
                elif '5' in list(key):
                    which_key = 'scanner_trigger'
                    logging.info(which_key)
                else:
                    which_key = False

                if which_key in ['1','2']:
                    logbids(template_bids.format(
                        onset=time.time()-run_start,
                        duration=0.,
                        stim_type='button_press',
                        stim_fn=which_key,
                        repeat='')
                        )
            # core.wait(time_fix_change-(time.time() - stim_start),hogCPUperiod=0.1)
            win.flip()
            stimulus.draw()
            fixation_dark.draw()
            win.logOnFlip('{0} onset 2'.format(trial_obj),level=logging.EXP)
            while time.time()-stim_start < 2.5:
                if serial_exists:
                    key = str(ser.read())
                else:
                    key = event.getKeys(['1','2','5'])

                if '1' in list(key):
                    which_key = '1'
                elif '2' in list(key):
                    which_key = '2'
                elif '5' in list(key):
                    which_key = 'scanner_trigger'
                    logging.info(which_key)
                else:
                    which_key = False

                if which_key in ['1','2']:
                    logbids(template_bids.format(
                        onset=time.time()-run_start,
                        duration=0.,
                        stim_type='button_press',
                        stim_fn=which_key,
                        repeat='')
                        )
            # core.wait(2.5-(time.time()-stim_start), hogCPUperiod=0.1)
        else:
            # normal fixation for the whole blank
            stimulus.draw()
            fixation.draw()
            win.logOnFlip('{0} onset 2'.format(trial_obj),level=logging.EXP)
            while time.time()-stim_start < 2.5:
                if serial_exists:
                    key = str(ser.read())
                else:
                    key = event.getKeys(['1','2','5'])

                if '1' in list(key):
                    which_key = '1'
                elif '2' in list(key):
                    which_key = '2'
                elif '5' in list(key):
                    which_key = 'scanner_trigger'
                    logging.info(which_key)
                else:
                    which_key = False

                if which_key in ['1','2']:
                    logbids(template_bids.format(
                        onset=time.time()-run_start,
                        duration=0.,
                        stim_type='button_press',
                        stim_fn=which_key,
                        repeat='')
                        )
            # core.wait(2.5-(time.time()-stim_start), hogCPUperiod=0.1)

        # second presentation
        win.flip()
        if fixation_change[trial] == 1 and (2.2 < time_fix_change < 2.5):
            stimulus.draw()
            fixation.draw()
            core.wait(time_fix_change-(time.time()-stim_start), hogCPUperiod=0.1)
            win.flip()
            fixation.draw()
            while time.time()-stim_start < 4.0:
                if serial_exists:
                    key = str(ser.read())
                else:
                    key = event.getKeys(['1','2','5'])

                if '1' in list(key):
                    which_key = '1'
                elif '2' in list(key):
                    which_key = '2'
                elif '5' in list(key):
                    which_key = 'scanner_trigger'
                    logging.info(which_key)
                else:
                    which_key = False

                if which_key in ['1','2']:
                    logbids(template_bids.format(
                        onset=time.time()-run_start,
                        duration=0.,
                        stim_type='button_press',
                        stim_fn=which_key,
                        repeat='')
                        )
            # core.wait(4.0-(time.time()-stim_start),hogCPUperiod=0.1)
        elif fixation_change[trial] == 1 and (2.5 < time_fix_change < 3.7):
            # dim fixation onset AND OFFSET during this presentation
            stimulus.draw()
            fixation_dark.draw()
            win.logOnFlip('fixation change onset', level=logging.EXP)
            core.wait(time_fix_change-(time.time()-stim_start),hogCPUperiod=0.1)

            win.flip()
            stimulus.draw()
            fixation.draw()
            while time.time()-stim_start < time_fix_change+.3:
                if serial_exists:
                    key = str(ser.read())
                else:
                    key = event.getKeys(['1','2','5'])

                if '1' in list(key):
                    which_key = '1'
                elif '2' in list(key):
                    which_key = '2'
                elif '5' in list(key):
                    which_key = 'scanner_trigger'
                    logging.info(which_key)
                else:
                    which_key = False

                if which_key in ['1','2']:
                    logbids(template_bids.format(
                        onset=time.time()-run_start,
                        duration=0.,
                        stim_type='button_press',
                        stim_fn=which_key,
                        repeat='')
                        )
            # core.wait(time_fix_change+.3-(time.time()-stim_start), hogCPUperiod=0.1)
            win.flip()
            stimulus.pos = [0,0] + .01*(np.random.randint(low=-3, high=3, size=2))
            fixation.draw()
            while time.time()-stim_start < 4.0:
                if serial_exists:
                    key = str(ser.read())
                else:
                    key = event.getKeys(['1','2','5'])

                if '1' in list(key):
                    which_key = '1'
                elif '2' in list(key):
                    which_key = '2'
                elif '5' in list(key):
                    which_key = 'scanner_trigger'
                    logging.info(which_key)
                else:
                    which_key = False

                if which_key in ['1','2']:
                    logbids(template_bids.format(
                        onset=time.time()-run_start,
                        duration=0.,
                        stim_type='button_press',
                        stim_fn=which_key,
                        repeat='')
                        )
            # core.wait(4.0-(time.time()-stim_start), hogCPUperiod=0.1)
        elif fixation_change[trial] == 1 and (3.7 <= time_fix_change < 4.0):
            # dim fixation onset, extends into blank
            stimulus.draw()
            fixation_dark.draw()
            win.logOnFlip('fixation change onset', level=logging.EXP)
            while time.time()-stim_start < time_fix_change:
                if serial_exists:
                    key = str(ser.read())
                else:
                    key = event.getKeys(['1','2','5'])

                if '1' in list(key):
                    which_key = '1'
                elif '2' in list(key):
                    which_key = '2'
                elif '5' in list(key):
                    which_key = 'scanner_trigger'
                    logging.info(which_key)
                else:
                    which_key = False

                if which_key in ['1','2']:
                    logbids(template_bids.format(
                        onset=time.time()-run_start,
                        duration=0.,
                        stim_type='button_press',
                        stim_fn=which_key,
                        repeat='')
                        )
            # core.wait(time_fix_change-(time.time()-stim_start), hogCPUperiod=0.1)
            win.flip()
            stimulus.pos = [0,0] + .01*(np.random.randint(low=-3, high=3, size=2))
            fixation_dark.draw()
        else:
            # fixation does not dim in this section
            stimulus.pos = [0,0] + .01*(np.random.randint(low=-3, high=3, size=2))
            fixation.draw()
            while time.time()-stim_start < 4.0:
                if serial_exists:
                    key = str(ser.read())
                else:
                    key = event.getKeys(['1','2','5'])

                if '1' in list(key):
                    which_key = '1'
                elif '2' in list(key):
                    which_key = '2'
                elif '5' in list(key):
                    which_key = 'scanner_trigger'
                    logging.info(which_key)
                else:
                    which_key = False

                if which_key in ['1','2']:
                    logbids(template_bids.format(
                        onset=time.time()-run_start,
                        duration=0.,
                        stim_type='button_press',
                        stim_fn=which_key,
                        repeat='')
                        )
            # core.wait(4.0-(time.time()-stim_start), hogCPUperiod=0.1)

        # second blank
        win.flip()
        if fixation_change[trial] == 1 and (3.7 < time_fix_change < 4.0):
            # finish dim fixation period, then draw regular
            fixation.draw()
            while time.time()-stim_start < time_fix_change+.3:
                if serial_exists:
                    key = str(ser.read())
                else:
                    key = event.getKeys(['1','2','5'])

                if '1' in list(key):
                    which_key = '1'
                elif '2' in list(key):
                    which_key = '2'
                elif '5' in list(key):
                    which_key = 'scanner_trigger'
                    logging.info(which_key)
                else:
                    which_key = False

                if which_key in ['1','2']:
                    logbids(template_bids.format(
                        onset=time.time()-run_start,
                        duration=0.,
                        stim_type='button_press',
                        stim_fn=which_key,
                        repeat='')
                        )
            # core.wait(time_fix_change+.3-(time.time()-stim_start), hogCPUperiod=0.1)
            win.flip()
            stimulus.draw()
            fixation.draw()
            win.logOnFlip('{0} onset 3'.format(trial_obj),level=logging.EXP)
            while time.time()-stim_start < 4.5:
                if serial_exists:
                    key = str(ser.read())
                else:
                    key = event.getKeys(['1','2','5'])

                if '1' in list(key):
                    which_key = '1'
                elif '2' in list(key):
                    which_key = '2'
                elif '5' in list(key):
                    which_key = 'scanner_trigger'
                    logging.info(which_key)
                else:
                    which_key = False

                if which_key in ['1','2']:
                    logbids(template_bids.format(
                        onset=time.time()-run_start,
                        duration=0.,
                        stim_type='button_press',
                        stim_fn=which_key,
                        repeat='')
                        )
            # core.wait(4.5-(time.time()-stim_start), hogCPUperiod=0.1)
        elif fixation_change[trial] == 1 and (4.0 <= time_fix_change < 4.2):
            # fixation dim happens all during the blank
            fixation_dark.draw()
            win.logOnFlip('fixation change onset', level=logging.EXP)
            while time.time()-stim_start < time_fix_change:
                if serial_exists:
                    key = str(ser.read())
                else:
                    key = event.getKeys(['1','2','5'])

                if '1' in list(key):
                    which_key = '1'
                elif '2' in list(key):
                    which_key = '2'
                elif '5' in list(key):
                    which_key = 'scanner_trigger'
                    logging.info(which_key)
                else:
                    which_key = False

                if which_key in ['1','2']:
                    logbids(template_bids.format(
                        onset=time.time()-run_start,
                        duration=0.,
                        stim_type='button_press',
                        stim_fn=which_key,
                        repeat='')
                        )
            # core.wait(time_fix_change-(time.time()-stim_start), hogCPUperiod=0.1)
            win.flip()
            fixation.draw()
            while time.time()-stim_start < time_fix_change+.3:
                if serial_exists:
                    key = str(ser.read())
                else:
                    key = event.getKeys(['1','2','5'])
                if key and key[-1] in ['1', '2', "b'1'","b'2'"]:
                    logbids(template_bids.format(
                        onset=time.time()-run_start,
                        duration=0.,
                        stim_type='button_press',
                        stim_fn=key[-1],
                        repeat='')
                    )
            # core.wait(time_fix_change+.3-(time.time()-stim_start), hogCPUperiod=0.1)
            win.flip()
            stimulus.draw()
            fixation.draw()
            while time.time()-stim_start < 4.5:
                if serial_exists:
                    key = str(ser.read())
                else:
                    key = event.getKeys(['1','2','5'])

                if '1' in list(key):
                    which_key = '1'
                elif '2' in list(key):
                    which_key = '2'
                elif '5' in list(key):
                    which_key = 'scanner_trigger'
                    logging.info(which_key)
                else:
                    which_key = False

                if which_key in ['1','2']:
                    logbids(template_bids.format(
                        onset=time.time()-run_start,
                        duration=0.,
                        stim_type='button_press',
                        stim_fn=which_key,
                        repeat='')
                        )
            # core.wait(4.5-(time.time()-stim_start), hogCPUperiod=0.1)
        elif fixation_change[trial] == 1 and (4.2 <= time_fix_change < 4.5):
            # fixation dims during the blank, extends into next presentation
            fixation_dark.draw()
            win.logOnFlip('fixation change onset', level=logging.EXP)
            core.wait(time_fix_change-(time.time()-stim_start), hogCPUperiod=0.1)
            win.flip()
            stimulus.draw()
            fixation_dark.draw()
            win.logOnFlip('{0} onset 3'.format(trial_obj),level=logging.EXP)
            while time.time()-stim_start < 4.5:
                if serial_exists:
                    key = str(ser.read())
                else:
                    key = event.getKeys(['1','2','5'])

                if '1' in list(key):
                    which_key = '1'
                elif '2' in list(key):
                    which_key = '2'
                elif '5' in list(key):
                    which_key = 'scanner_trigger'
                    logging.info(which_key)
                else:
                    which_key = False

                if which_key in ['1','2']:
                    logbids(template_bids.format(
                        onset=time.time()-run_start,
                        duration=0.,
                        stim_type='button_press',
                        stim_fn=which_key,
                        repeat='')
                        )
            # core.wait(4.5-(time.time()-stim_start), hogCPUperiod=0.1)
        else:
            # normal fixation for the whole blank
            stimulus.draw()
            fixation.draw()
            win.logOnFlip('{0} onset 3'.format(trial_obj),level=logging.EXP)
            while time.time()-stim_start < 4.5:
                if serial_exists:
                    key = str(ser.read())
                else:
                    key = event.getKeys(['1','2','5'])

                if '1' in list(key):
                    which_key = '1'
                elif '2' in list(key):
                    which_key = '2'
                elif '5' in list(key):
                    which_key = 'scanner_trigger'
                    logging.info(which_key)
                else:
                    which_key = False

                if which_key in ['1','2']:
                    logbids(template_bids.format(
                        onset=time.time()-run_start,
                        duration=0.,
                        stim_type='button_press',
                        stim_fn=which_key,
                        repeat='')
                        )
            # core.wait(4.5-(time.time()-stim_start), hogCPUperiod=0.1)

        # third presentation
        win.flip()
        if fixation_change[trial] == 1 and (4.2 < time_fix_change < 4.5):
            stimulus.draw()
            fixation.draw()
            core.wait(time_fix_change-(time.time()-stim_start), hogCPUperiod=0.1)
            win.flip()
            if serial_exists:
                key = str(ser.read())
            else:
                key = event.getKeys(['1','2','5'])

            if '1' in list(key):
                which_key = '1'
            elif '2' in list(key):
                which_key = '2'
            elif '5' in list(key):
                which_key = 'scanner_trigger'
                logging.info(which_key)
            else:
                which_key = False

            if which_key in ['1','2']:
                logbids(template_bids.format(
                    onset=time.time()-run_start,
                    duration=0.,
                    stim_type='button_press',
                    stim_fn=which_key,
                    repeat='')
                    )
        elif fixation_change[trial] == 1 and (4.2 <= time_fix_change < 4.5):
            # finish dim fixation
            stimulus.draw()
            fixation.draw()
            while time.time()-stim_start < time_fix_change+.3:
                if serial_exists:
                    key = str(ser.read())
                else:
                    key = event.getKeys(['1','2','5'])

                if '1' in list(key):
                    which_key = '1'
                elif '2' in list(key):
                    which_key = '2'
                elif '5' in list(key):
                    which_key = 'scanner_trigger'
                    logging.info(which_key)
                else:
                    which_key = False

                if which_key in ['1','2']:
                    logbids(template_bids.format(
                        onset=time.time()-run_start,
                        duration=0.,
                        stim_type='button_press',
                        stim_fn=which_key,
                        repeat='')
                        )
            # core.wait(time_fix_change+.3-(time.time()-stim_start), hogCPUperiod=0.1)
            win.flip()
        if fixation_change[trial] == 1 and time_fix_change > 4.5:
            # fixation dims during this presentation
            win.logOnFlip('fixation change onset', level=logging.EXP)
            stimulus.draw()
            fixation_dark.draw()
            while time.time()-stim_start < time_fix_change:
                if serial_exists:
                    key = str(ser.read())
                else:
                    key = event.getKeys(['1','2','5'])

                if '1' in list(key):
                    which_key = '1'
                elif '2' in list(key):
                    which_key = '2'
                elif '5' in list(key):
                    which_key = 'scanner_trigger'
                    logging.info(which_key)
                else:
                    which_key = False

                if which_key in ['1','2']:
                    logbids(template_bids.format(
                        onset=time.time()-run_start,
                        duration=0.,
                        stim_type='button_press',
                        stim_fn=which_key,
                        repeat='')
                        )
            # core.wait(time_fix_change-(time.time()-stim_start), hogCPUperiod=0.1)
            win.flip()
            stimulus.draw()
            fixation.draw()
            while time.time()-stim_start < time_fix_change+.3:
                if serial_exists:
                    key = str(ser.read())
                else:
                    key = event.getKeys(['1','2','5'])

                if '1' in list(key):
                    which_key = '1'
                elif '2' in list(key):
                    which_key = '2'
                elif '5' in list(key):
                    which_key = 'scanner_trigger'
                    logging.info(which_key)
                else:
                    which_key = False

                if which_key in ['1','2']:
                    logbids(template_bids.format(
                        onset=time.time()-run_start,
                        duration=0.,
                        stim_type='button_press',
                        stim_fn=which_key,
                        repeat='')
                        )
            # core.wait(time_fix_change+.3-(time.time()-stim_start), hogCPUperiod=0.1)
            win.flip()

        while time.time()-stim_start < 6.0:
            if serial_exists:
                key = str(ser.read())
            else:
                key = event.getKeys(['1','2','5'])

            if '1' in list(key):
                which_key = '1'
            elif '2' in list(key):
                which_key = '2'
            elif '5' in list(key):
                which_key = 'scanner_trigger'
                logging.info(which_key)
            else:
                which_key = False

            if which_key in ['1','2']:
                logbids(template_bids.format(
                    onset=time.time()-run_start,
                    duration=0.,
                    stim_type='button_press',
                    stim_fn=which_key,
                    repeat='')
                    )
        # core.wait(6.0-(time.time()-stim_start), hogCPUperiod=0.1)

    else:
        # show the sketch
        if fixation_change[trial] == 1:
            time_fix_change = .5+5*(np.random.uniform(low=0.,high=1.,size=1))
            logging.exp('time of fixation change is {0}'.format(time_fix_change))
        now = time.time()
        fix_wait = True
        while stimulus.status != visual.FINISHED:
            stimulus.draw()
            if fixation_change[trial] == 0 or now-stim_start < time_fix_change:
                fixation.draw()
            elif now-(stim_start+time_fix_change) > 0.3:
                fixation.draw()
            elif fix_wait:
                fixation_dark.draw()
                win.logOnFlip('fixation change onset', level=logging.EXP)
                fix_wait = False
            else:
                fixation_dark.draw()

            if serial_exists:
                key = str(ser.read())
            else:
                key = event.getKeys(['1','2','5'])

            if '1' in list(key):
                which_key = '1'
            elif '2' in list(key):
                which_key = '2'
            elif '5' in list(key):
                which_key = 'scanner_trigger'
                logging.info(which_key)
            else:
                which_key = False

            if which_key in ['1','2']:
                logbids(template_bids.format(
                    onset=time.time()-run_start,
                    duration=0.,
                    stim_type='button_press',
                    stim_fn=which_key,
                    repeat='')
                    )
            now = time.time()
            win.flip()

    fixation.draw()
    win.flip()
    fix_start = time.time()

    print("Stimulus {0} was on for {1}".format(trial_obj+'_'+stim_type,fix_start-stim_start))

    # if fixation_change[trial] == 1:
    #     logbids(template_bids.format(
    #             onset=stim_start+time_fix_change-run_start,
    #             duration=0.3,
    #             stim_type='fixChange',
    #             stim_fn='fixDark',
    #             repeat='')
    #         )

    # log the trial
    logbids(template_bids.format(
            onset=stim_start-run_start,
            duration=time.time()-stim_start,
            stim_type=stim_type,
            stim_fn=trial_obj,
            repeat=bRepeat)
        )

    while time.time()-stim_start <=durations[trial]+2-trial_jitters[trial]:
        fixation.draw()
        win.flip()

    print("Fixation was on screen for {0}".format(time.time()-fix_start))

    if serial_exists:
        key = str(ser.read())
    else:
        key = event.getKeys(['1','2','5'])

    if '1' in list(key):
        which_key = '1'
    elif '2' in list(key):
        which_key = '2'
    elif '5' in list(key):
        which_key = 'scanner_trigger'
        logging.info(which_key)
    else:
        which_key = False

    if which_key in ['1','2']:
        logbids(template_bids.format(
            onset=time.time()-run_start,
            duration=0.,
            stim_type='button_press',
            stim_fn=which_key,
            repeat='')
            )

core.wait(8, hogCPUperiod=0.1)

finished = "Finished run successfully!"
logging.info(finished)
print(finished)
win.close()
print('quitting because end of experiment...')
core.quit()
