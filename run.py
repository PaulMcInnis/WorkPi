"""Work logging tool based on raspberry pi TFT TODO: JIRA integ."""
from collections import namedtuple
from datetime import timedelta, datetime
from enum import Enum
import os, sys, sched, time
from typing import List
from gpiozero import Button
import pygame
from pygame.locals import KEYDOWN, K_ESCAPE, K_DOWN, K_UP, K_RETURN, K_BACKSPACE, KMOD_NONE
from roundrects import round_rect

# Setup touchscreen
os.environ["SDL_FBDEV"] = "/dev/fb1"
os.environ["SDL_MOUSEDEV"] = "/dev/input/touchscreen"
os.environ["SDL_MOUSEDRV"] = "TSLIB"

# Inits TODO: move some of these into WorkDisplay
SCREEN_HEIGHT = 240
SCREEN_WIDTH = 320
SCREEN_SIZE = (SCREEN_WIDTH, SCREEN_HEIGHT)
NUM_JOBS_DISPLAYED = 5
ENC_A_PIN = 14  # Note these are not the actual rpi pin #'s but the BCM #s
ENC_B_PIN = 15
SW_PIN = 23
TIMER_REFRESH_SECONDS = 1

# NOTE: OpenSans license (Apache 2.0) here: https://www.fontsquirrel.com/license/open-sans
ID_FONT = '/home/pi/WorkPi/OpenSans-Semibold.ttf'  # FIXME these paths are gonna be wrong for users.
TIME_FONT = '/home/pi/WorkPi/OpenSans-Regular.ttf'
DESC_FONT = '/home/pi/WorkPi/OpenSans-LightItalic.ttf'

SELECTOR_WIDTH = SCREEN_WIDTH - 8
SELECTOR_HEIGHT = int(SCREEN_HEIGHT / NUM_JOBS_DISPLAYED) - 8

# TODO move into WorkDisplay
BLACK = (0, 0, 0)
BG_COLOUR = (39, 40, 34)
DESC_COLOUR = (230, 219, 116)
ID_COLOUR = (174, 129, 255)
HIGHLIGHT_COLOUR = (249, 38, 114)
TIME_COLOUR = (253, 151, 31)

class Direction(Enum):
    UP = 1
    DOWN = 2


class DisplayMode(Enum):
    SELECTOR = 1
    TIMER = 2


class Job(object):
    def __init__(self, id: str, desc: str, elapsed: timedelta):
        """Just a container for the job id, description and elapsed time"""
        self.id = id
        self.desc = desc
        self.elapsed = elapsed


class WorkDisplay(object):
    """Parent class with the fonts etc"""

    def __init__(self) -> None:
        self.id_font = pygame.font.Font(ID_FONT, 16)
        self.desc_font = pygame.font.Font(DESC_FONT, 14)
        self.small_time_font = pygame.font.Font(TIME_FONT, 12)
        self.large_time_font = pygame.font.Font(TIME_FONT, 24)

    def get_days_hours_minutes_string(self, td: timedelta, show_seconds: bool = False) -> str:
        days = td.days
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        seconds += td.microseconds / 1e6
        ret_str = ""
        if days:
            ret_str += "{}d ".format(days)
        if hours:
            ret_str += "{}h ".format(hours)
        if minutes:
            ret_str += "{}m ".format(minutes)
        if show_seconds:
            ret_str += "{:.0f}s".format(seconds)
        return ret_str


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
        small_time = self.small_time_font.render(
            self.get_days_hours_minutes_string(job.elapsed), 1, (TIME_COLOUR))
        small_time_width = self.small_time_font.size(
            self.get_days_hours_minutes_string(job.elapsed))[0]
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
        self.start_time = None
        self.time_elapsed = None  # this goes into self.job when we stop()

    def set_job(self, job: Job) -> None:
        """Update the job"""
        self.job = job

    def start(self) -> None:
        """Start the timer"""
        self.start_time = datetime.now()
        self.time_elapsed = timedelta(0)
        self.running = True

    def stop(self) -> None:
        """Stop the timer, and update"""
        self.start_time = None
        self.job.elapsed += self.time_elapsed
        self.time_elapsed = None

    def update_elapsed(self) -> None:
        """Update self.job's elapsed time based on start time"""
        if self.start_time:
            self.time_elapsed = datetime.now() - self.start_time
        else:
            raise ValueError("Timer not started")

    def draw(self) -> None:
        """Draw the entire logging screen"""
        screen.fill(BLACK)
        round_rect(screen, (5, 5, SELECTOR_WIDTH, SCREEN_HEIGHT * .10), BG_COLOUR, 8)
        round_rect(
            screen, (5, SCREEN_HEIGHT * .15, SELECTOR_WIDTH, SCREEN_HEIGHT * .57), BG_COLOUR, 8)
        round_rect(screen, (5, SCREEN_HEIGHT * .75, SELECTOR_WIDTH, 56), BG_COLOUR, 8)

        screen.blit(self.id_font.render(self.job.id, 1, (ID_COLOUR)), (10, 5))

        disp_time_string = self.get_days_hours_minutes_string(
            self.job.elapsed + self.time_elapsed, show_seconds=True)
        dis_time_width = self.large_time_font.size(disp_time_string)[0]
        screen.blit(
            self.large_time_font.render(
                disp_time_string,
                1,
                (TIME_COLOUR)
            ),
            (SELECTOR_WIDTH/2 - dis_time_width // 2, SCREEN_HEIGHT * .80)
        )

        # FIXME: below should be replaced with something better, hard to change (diff screen)
        max_line_len = 45 # chars
        xoffset, yoffset, spacing = 15, 40, 17
        ymax = SCREEN_HEIGHT * .53
        i, j, y = 0, 0, 0
        while i < len(self.job.desc):

            # we only wanna blit stuff one line at a time...
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
    print('initializing')
    pygame.init()
    pygame.mouse.set_visible(False)

    # TODO sync with JIRA!
    # TODO: remove
    # lets make some spoof jobs to display
    SPOOF_DESCS = [
        "Get rid of databases and import everything into CSVs so that nothing ever crashes",
        "The company car needs washing.",
        "Need to add a new user to JIRA.",
        "Re-write fused-batchnorms in tf.keras so that is_training ACTUALLY works when you freeze it.",
    ]

    SPOOF_TIMES = [
        timedelta(days=3, minutes=45, seconds=18),
        timedelta(days=0, minutes=45, seconds=0),
        timedelta(days=0, minutes=10, seconds=15),
        timedelta(days=15, minutes=2, seconds=42),
    ]

    SPOOF_JOBS = [
            Job('DE-1132', SPOOF_DESCS[0], SPOOF_TIMES[0]),
            Job('ZD-8913', SPOOF_DESCS[1], SPOOF_TIMES[1]),
            Job('JI-1121', SPOOF_DESCS[2], SPOOF_TIMES[2]),
            Job('KR-7613', SPOOF_DESCS[3], SPOOF_TIMES[3]),
    ]

    # extend with random mixes
    for i in range (5):
        SPOOF_JOBS.append(Job('ZJ-{}000'.format(i) , choice(SPOOF_DESCS), choice(SPOOF_TIMES)))


    # Init disp
    mode = DisplayMode.SELECTOR
    timer = TimerDisplay(SPOOF_JOBS[0])
    selector = JobDisplay(SPOOF_JOBS)
    screen = pygame.display.set_mode(SCREEN_SIZE)
    selector.draw()
    update_display = True

    # Init I/O
    enc_a = Button(ENC_A_PIN, pull_up=True)
    enc_b = Button(ENC_B_PIN, pull_up=True)
    def enc_a_rising():
        if enc_b.is_pressed:
            pygame.event.post(
                pygame.event.Event(
                    pygame.locals.KEYDOWN,
                    key=K_DOWN,
                    mod=KMOD_NONE
                )
            )
    def enc_b_rising():
        if enc_a.is_pressed:
            pygame.event.post(
                pygame.event.Event(
                    pygame.locals.KEYDOWN,
                    key=K_UP,
                    mod=KMOD_NONE
                )
            )
    enc_a.when_pressed = enc_a_rising
    enc_b.when_pressed = enc_b_rising

    button = Button(SW_PIN, pull_up=True)
    def __enter_or_exit_timer_screen():
        # pressing rotary encoder raises same event as pressing enter
        pygame.event.post(
            pygame.event.Event(
                pygame.locals.KEYDOWN,
                key=K_RETURN,
                mod=KMOD_NONE
            )
        )
    button.when_pressed = __enter_or_exit_timer_screen

    # Interact + draw loop
    print("running")
    last_update_time = time.time()
    while True:

        # Get any input events
        pyg_events = pygame.event.get()
        if pyg_events:
            update_display = True

        # Manipulate UI via input events
        for event in pyg_events:
            if event.type == KEYDOWN:
                if mode == DisplayMode.SELECTOR:
                    if event.key == K_ESCAPE:
                        sys.exit()
                    elif event.key == K_DOWN:
                        selector.move_selection(Direction.DOWN)
                    elif event.key == K_UP:
                        selector.move_selection(Direction.UP)
                    elif event.key == K_RETURN:
                        # start timer
                        timer.set_job(selector.get_job())
                        mode = DisplayMode.TIMER
                        timer.start()

                elif mode == DisplayMode.TIMER:
                    if event.key == K_ESCAPE or event.key == K_RETURN:
                        mode = DisplayMode.SELECTOR
                    timer.stop()

        # Draw screen if we saw any events or it's been enough second(s) (for the timer)
        cur_time = time.time()
        update_timer_elapsed = (
            mode == DisplayMode.TIMER and cur_time - last_update_time >= TIMER_REFRESH_SECONDS)
        if update_display or update_timer_elapsed:

            if update_timer_elapsed:
                timer.update_elapsed()

            if mode == DisplayMode.SELECTOR:
                selector.draw()
            elif mode == DisplayMode.TIMER:
                timer.draw()
            else:
                raise ValueError("UNKNOWN MODE")
            pygame.display.update()

            last_update_time = cur_time
            update_display = False
