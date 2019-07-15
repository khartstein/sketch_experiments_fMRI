#!/usr/bin/env python

# Run this from the command line from 'sketch-morph/fMRI/exp2' directory using:
#   python exp2_instructs.py

import sys
import numpy as np
from os import makedirs
from os.path import join, exists, abspath, dirname
from psychopy import visual, core, event, gui, logging, sound
from psychopy.constants import (NOT_STARTED, STARTED, PLAYING, PAUSED,
                                STOPPED, FINISHED, PRESSED, RELEASED, FOREVER)


# Set up all the relevant directories here
HERE = abspath(dirname(__file__))
STIMDIR = join(HERE, "stim")

objects = ['pig_alarm-clock','hedgehog_bush','hand_cactus','face_radio',
           'face_strawberry','foot_hockey-stick','rabbit_scissors','lion_sun']

sub_objects = np.random.permutation(objects)

# Open window

# # for scanner projector
# win = visual.Window([1280,960], screen=0, fullscr=True, color=(128,128,128),
#                     colorSpace='rgb255', name='Window')

# for testing
win = visual.Window([1680,1050], screen=0, fullscr=True, color=(128,128,128),
                    colorSpace='rgb255', name='Window')

# concentric circles for fixation
fixation_fn = join(HERE, 'fixation_green_thumb.png')
fixation = visual.ImageStim(win, fixation_fn, name='Fixation', colorSpace='rgb', autoLog=True)

# load stimuli
stimuli = {}
load_text = "Loading stimuli..."
load_disp = visual.TextStim(win, text=load_text,
                               alignHoriz='center', alignVert='center',
                               name='Loading', color='black')
load_disp.draw()
win.flip()

for obj_no in range(len(sub_objects)):
    trial_obj = sub_objects[obj_no]    # object category
    stim_number = 0    # which exemplar

    # load the sketch video
    clip_fn = join(STIMDIR, trial_obj+'_'+str(stim_number)+'_8s.mov')
    stimuli[obj_no] = visual.MovieStim3(win, clip_fn,
                                pos=(0, 0), flipVert=False,
                                flipHoriz=False, loop=False,
                                noAudio=True, name=trial_obj)

instructions = visual.TextStim(win, wrapWidth=1.8,
                alignHoriz='center', alignVert='center', name='Instructions',
                text=("In this experiment, you will view ambiguous sketches of objects. \n\n"
                      "For each ambiguous sketch, there are two alternative interpretations. \n\n"
                      "Each of these alternatives is an object category \n"
                      "from the first experiment.\n\n"
                      "Next, you will see some examples of the ambiguous sketches."),
                color='black')
                # pos=[-.9, .6]

instructions.draw()
win.flip()

instructions_wait = True
while instructions_wait:
    keys = event.getKeys()
    if 'space' in keys or 'return' in keys:
        print("Finished instructions")
        instructions_wait = False
    if 'q' in keys or 'escape' in keys:
        quitting = ('Quit command ("q" or "escape") was detected! '
                    'Quitting experiment')
        print(quitting)
        win.close()
        core.quit()

win.mouseVisible = False

# Start fixation
fixation.draw()
win.flip()
core.wait(2., hogCPUperiod=0.2)

# Start looping through trials
for obj_no in range(len(sub_objects)):
    # prepare stimulus for this trial
    stimulus = stimuli[obj_no]

    # show names of alternatives
    names = sub_objects[obj_no].split('_')
    animate_name = names[0]
    inanimate_name = names[1]

    if np.random.rand() >= .5:
        right_text = animate_name
        left_text = inanimate_name
    else:
        right_text = inanimate_name
        left_text = animate_name

    # center_text = 'or neither of these'
    question_text = 'Possible interpretations for sketch identity: '
    probe_left = visual.TextStim(win, text=left_text, pos=(-.3, 0),
                                 alignHoriz='center', alignVert='center',
                                 name='Left probe', color ='black')
    probe_right = visual.TextStim(win, text=right_text, pos=(.3, 0),
                                  alignHoriz='center', alignVert='center',
                                  name='Right probe', color='black')
    # probe_center = visual.TextStim(win, text=center_text, pos=(0,-.3),
    #                               alignHoriz='center', alignVert='center',
    #                               name='Bottom probe', color='black')
    question = visual.TextStim(win, text=question_text, pos=(0, .4), alignHoriz='center',
                       alignVert='bottom', wrapWidth=2, color='black', name='What object?')


    question.draw()
    probe_left.draw()
    probe_right.draw()
    win.flip()

    core.wait(2., hogCPUperiod=0.2)
    fixation.draw()
    win.flip()
    core.wait(2., hogCPUperiod=0.2)

    # show the sketch
    while stimulus.status != visual.FINISHED:
        stimulus.draw()
        fixation.draw()
        win.flip()

    fixation.draw()
    win.flip()
    core.wait(2, hogCPUperiod=0.2)

core.wait(4., hogCPUperiod=0.2)

lay_still = visual.TextStim(win, wrapWidth=1.8,
                alignHoriz='center', alignVert='center', name='Instructions',
                text=("Please lay still for the rest of the anatomical scan, \n"
                      "After that, we will begin the experiment. \n\n"
                      "In part one, you will view ambiguous sketches \n"
                      "and report what you saw. \n\n"
                      "In part two, you will attempt to interpret each ambiguous sketch \n"
                      "as a specific alternative."),
                color='black')
                # pos=[-.9, .6]

lay_still.draw()
win.flip()

lay_still_wait = True
while lay_still_wait:
    keys = event.getKeys()
    if 'space' in keys or 'return' in keys:
        print("Finished lay_still")
        lay_still_wait = False
    if 'q' in keys or 'escape' in keys:
        quitting = ('Quit command ("q" or "escape") was detected! '
                    'Quitting experiment')
        print(quitting)
        win.close()
        core.quit()


finished = "Finished instructions successfully!"
print(finished)
win.close()
core.quit()
