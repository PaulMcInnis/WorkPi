"""Work logging tool based on raspberry pi TFT TODO: JIRA integ."""
from collections import namedtuple
from datetime import datetime
from enum import Enum
import os, sys
from typing import List
import pygame
from pygame.locals import KEYDOWN, K_ESCAPE, K_DOWN, K_UP, K_RETURN

from roundrects import round_rect
from gaugette import Switch, RotaryEncoder, Gpio


# Setup touchscreen
os.environ["SDL_FBDEV"] = "/dev/fb1"
os.environ["SDL_MOUSEDEV"] = "/dev/input/touchscreen"
os.environ["SDL_MOUSEDRV"] = "TSLIB"

# Inits
SCREEN_HEIGHT = 240
SCREEN_WIDTH = 320
SCREEN_SIZE = (SCREEN_WIDTH, SCREEN_HEIGHT)
NUM_JOBS_DISPLAYED = 5
ENC_A_PIN = 17  # Note these are not the actual rpi pin #'s but the BCM #s
ENC_B_PIN = 18
SW_PIN = 27

# NOTE: OpenSans license (Apache 2.0) here: https://www.fontsquirrel.com/license/open-sans
ID_FONT = './OpenSans-Semibold.ttf'  # FIXME these paths are gonna be wrong for users.
TIME_FONT = './OpenSans-Regular.ttf'
DESC_FONT = './OpenSans-LightItalic.ttf'
LOREM_IPSUM = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor "\
    "incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud "\
    "exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor"\
    " in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur"\
    " sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est"\
    " laborum."

SELECTOR_WIDTH = SCREEN_WIDTH - 8
SELECTOR_HEIGHT = int(SCREEN_HEIGHT / NUM_JOBS_DISPLAYED) - 8

BLACK = (0, 0, 0)
BG_COLOUR = (39, 40, 34)
DESC_COLOUR = (230, 219, 116)
ID_COLOUR = (174, 129, 255)
HIGHLIGHT_COLOUR = (249, 38, 114)
TIME_COLOUR = (253, 151, 31)

Job = namedtuple('Job', 'id desc elapsed')


class Direction(Enum):
    UP = 1
    DOWN = 2

class DisplayMode(Enum):
    SELECTOR = 1
    TIMER = 2

class WorkDisplay(object):
    """Parent class with the fonts etc"""

    def __init__(self) -> None:
        self.id_font = pygame.font.Font(ID_FONT, 16)
        self.desc_font = pygame.font.Font(DESC_FONT, 14)
        self.small_time_font = pygame.font.Font(TIME_FONT, 12)
        self.large_time_font = pygame.font.Font(TIME_FONT, 24)


class JobDisplay(WorkDisplay):
    """Class to show and select from assigned/in-progress jobs"""

    def __init__(self, jobs_list: List[Job]) -> None:
        super().__init__()

        self.jobs_list = jobs_list
        self.sel_idx = 0
        self.displayed_jobs_min = 0
        self.displayed_jobs_max = NUM_JOBS_DISPLAYED - 1

    def get_job(self) -> Job:
        """Get the currently selected job"""
        return self.jobs_list[self.sel_idx]

    def draw_selection_item(self, job: Job, x: int, y: int) -> None:
        """Draw a button for the task selection screen"""
        round_rect(screen, (x, y, SELECTOR_WIDTH, SELECTOR_HEIGHT), BG_COLOUR, 6)
        screen.blit(self.id_font.render(job.id, 1, (ID_COLOUR)), (x + 5, y))
        screen.blit(
            self.desc_font.render(
                job.desc[:40] + '...' if len(job.desc) > 43 else job.desc,
                1,
                (DESC_COLOUR)),
            (x + 5, y + 20)
        )
        # FIXME: use time() here
        small_time = self.small_time_font.render(str(job.elapsed), 1, (TIME_COLOUR))
        small_time_width = self.small_time_font.size(str(job.elapsed))[0]
        screen.blit(
            small_time,
            (x + SELECTOR_WIDTH - 5 - small_time_width, y + 5),
        )

    def __highlight_selection(self, x: int, y: int) -> None:
        """Draw the highlighting to show what job is selected"""
        round_rect(screen, (x-2, y-2, SELECTOR_WIDTH + 4, SELECTOR_HEIGHT + 4), HIGHLIGHT_COLOUR, 6)

    def move_selection(self, direction: Direction) -> None:
        """Move selection up/down, handles updating what will be displayed"""
        if direction == Direction.DOWN:
            if self.sel_idx < len(self.jobs_list) - 1:
                self.sel_idx += 1
                if self.sel_idx > self.displayed_jobs_max:
                    self.displayed_jobs_min += 1
                    self.displayed_jobs_max += 1
        else:
            if self.sel_idx > 0:
                self.sel_idx -= 1
                if self.sel_idx < self.displayed_jobs_min:
                    self.displayed_jobs_min -= 1
                    self.displayed_jobs_max -= 1

    def draw(self) -> None:
        """Draw the entire job selection screen"""
        offset = 7 + SELECTOR_HEIGHT
        x, y = 4, 5
        screen.fill(BLACK)
        for i in range(self.displayed_jobs_min, self.displayed_jobs_max + 1):

            # If this job is selected, hightlight it
            if i == self.sel_idx:
                self.__highlight_selection(x, y)

            # Draw the job + offset y each time
            self.draw_selection_item(self.jobs_list[i], x, y)
            y += offset


class TimerDisplay(WorkDisplay):
    """Class to show the time being logged + the job id + desc that it's being logged to"""

    def __init__(self, job: Job) -> None:
        super().__init__()
        self.job = job
        self.time = datetime.now()

    def set_job(self, job: Job) -> None:
        """Update the job"""
        self.job = job

    def draw(self) -> None:
        """Draw the entire logging screen"""
        screen.fill(BLACK)
        round_rect(screen, (5, 5, SELECTOR_WIDTH, SCREEN_HEIGHT * .10), BG_COLOUR, 8)
        round_rect(
            screen, (5, SCREEN_HEIGHT * .15, SELECTOR_WIDTH, SCREEN_HEIGHT * .57), BG_COLOUR, 8)
        round_rect(screen, (5, SCREEN_HEIGHT * .75, SELECTOR_WIDTH, 56), BG_COLOUR, 8)

        screen.blit(self.id_font.render(self.job.id, 1, (ID_COLOUR)), (10, 5))
        screen.blit(
            self.large_time_font.render(
                self.job.elapsed,
                1,
                (TIME_COLOUR)
            ),
            (SELECTOR_WIDTH/2 - 30, SCREEN_HEIGHT * .80)
        )

        # FIXME: this should be replaced with something better, will be hard to change (diff screen)
        max_line_len = 45 # chars
        xoffset = 15
        yoffset = 40
        spacing = 17
        ymax = SCREEN_HEIGHT * .53
        i, j, y = 0, 0, 0
        while i < len(self.job.desc):

            # this is buggy...
            last_whitesp_idx = self.job.desc[i : i + max_line_len].rfind(' ')
            line = self.job.desc[i : i + last_whitesp_idx + 1]
            y = yoffset + j * spacing

            if y >= ymax:
                line += '...'

            screen.blit(
                self.desc_font.render(
                    line,
                    1,
                    (DESC_COLOUR)),
                (xoffset, y)
            )

            if y > ymax:
                break
            j += 1
            i += last_whitesp_idx + 1

if __name__ == "__main__":
    # init
    pygame.init()
    pygame.mouse.set_visible(False)

    # Get job data TODO: Query JIRA
    jobs_list = [
        Job('DE-3334', LOREM_IPSUM,'0h 0m'),
        Job('PS-6451', LOREM_IPSUM,'3h 15m'),
        Job('PS-1121', LOREM_IPSUM,'1h 6m'),
        Job('DE-7613', LOREM_IPSUM,'11h 6m'),
        Job('DE-4242', LOREM_IPSUM,'2d 11h 6m'),
    ]
    jobs_list.extend(jobs_list)

    # Init disp
    mode = DisplayMode.SELECTOR
    timer = TimerDisplay(jobs_list[0])
    selector = JobDisplay(jobs_list)
    screen = pygame.display.set_mode(SCREEN_SIZE)
    selector.draw()

    # Init rotary enc
    encoder = RotaryEncoder(Gpio(), ENC_A_PIN, ENC_B_PIN)
    encoder.start()

    # Interact + draw loop
    while True:
        update_display = False  # FIXME: make this go every second vs on-event in timer screen

        # Handle rotary encoder
        delta = encoder.get_cycles()
        if delta != 0:
            print ("rotated {}".format(delta))

            update_display = True
            if delta < 0:
                selector.move_selection(Direction.DOWN)
            elif delta > 0:
                selector.move_selection(Direction.UP)

        # Handle general I/O (i.e. keyboard)
        for event in pygame.event.get():

            # debug coords for touch screen
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = (pygame.mouse.get_pos() [0], pygame.mouse.get_pos() [1])
                # on_touch() TODO
                print("mouse on pos {}".format(pos))

            # handle keys
            if event.type == KEYDOWN: # TODO implement encoder
                if mode == DisplayMode.SELECTOR:
                    if event.key == K_ESCAPE:
                        print("kescape: EXIT TO TERMINAL")
                        sys.exit()
                    elif event.key == K_DOWN:
                        print("kdown")
                        selector.move_selection(Direction.DOWN)
                    elif event.key == K_UP:
                        selector.move_selection(Direction.UP)
                        print("kup")
                    elif event.key == K_RETURN:
                        mode = DisplayMode.TIMER
                        timer.set_job(selector.get_job())
                        print("kenter")
                elif mode == DisplayMode.TIMER:
                    if event.key == K_ESCAPE:
                        mode = DisplayMode.SELECTOR
                        print("kescape: EXIT TO SELECTOR")

            update_display = True

        # Update screen
        if update_display:
            if mode == DisplayMode.SELECTOR:
                selector.draw()
            elif mode == DisplayMode.TIMER:
                timer.draw()
            else:
                raise ValueError("UNKNOWN MODE")
            pygame.display.update()
