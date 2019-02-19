import cocos
import json
import random
from cocos.director import director
from cocos.audio.pygame.mixer import Sound
from cocos.audio.pygame import mixer
from cocos.actions import MoveBy, Reverse, FadeIn, FadeOut, Waves
from lisp_std_env import std_env
import os

import pyglet

# spritesheet = pyglet.image.load("testsprite.png")
# grid = pyglet.image.ImageGrid(spritesheet, 2, 2)
# textures = pyglet.image.TextureGrid(grid)
# anim = pyglet.image.Animation.from_image_sequence(textures, 1)

_BUTTONS = ['RIGHT', 'LEFT', 'Z', 'X']


def r_path(relative):
    return os.path.abspath(relative)
    # if hasattr(sys, "_MEIPASS"):
    #     return os.path.join(sys._MEIPASS, relative)
    # return os.path.join(relative)


class SpriteStorage(cocos.cocosnode.CocosNode):
    """
    Wrapper class to handle animootions
    """
    anim_stages = []
    anim_step = 0
    anim_counter = 0
    anim_loop = False
    anim_ended = False
    env = {}

    def __init__(self, anim, env):
        super(SpriteStorage).__init__()
        self.anim_stages = anim
        self.env = env
        self.anim_step = 0
        self.anim_counter = 0
        self.anim_loop = any(x.get('loop', False) for x in self.anim_stages)
        self.anim_ended = False

    def anim_end(self):
        return self.anim_loop or self.anim_ended

    def update(self, dt):
        self.anim_counter = min(self.anim_stages[self.anim_step].get('time', 0), self.anim_counter + dt)



class StateMachine(cocos.cocosnode.CocosNode):
    """
    A class for loading and storing a state machine.
    states - a dict of different states that the machine goes through.
    storage - a dict of environment variables specific to the machine
    resources - a dict of resources the machine uses, for preloading.
    sprite - a Cocos2Dpy sprite (hopefully this works)
    key_events - a dict of key events
    """
    states = {}
    resouces = {}
    storage = {}
    current_state = None
    timer = 0
    anim = 0
    key_events = None
    sprite = None

    def eval_action(self, a, env={}):
        """
        Evaluates actions and checks in a lisp-like manner
        :param a: action being evaluated, a list like ["+", 1, 1]
        :param env:
        :return:
        """
        if isinstance(a, str):
            # getting value of a variable
            return self.storage.get(a, env.get(a))
        elif not isinstance(a, list):
            return a
        elif a[0] in ['q', 'quote']:
            # getting around it trying to find any string as a variable
            return str(a[1])
        elif a[0] == 'if':
            # conditional execution
            if self.eval_action(a[1], env):
                return self.eval_action(a[2], env)
            elif len(a) > 3:
                return self.eval_action(a[3], env)
            else:
                return None
        elif a[0] == ':=':
            if a[1] in self.storage:
                self.storage[a[1]] = self.eval_action(a[2], env)
            elif a[1] in eval:
                env[a[1]] = self.eval_action(a[2], env)
            else:
                print(f"Could not find variable {a[1]}")
        elif a[0] == 'def':
            env[a[1]] = self.eval_action(a[2], env)
        elif a[0] == 'win_fight':
            env['fight_over'] = True
        else:
            return self.eval_action(a[0], env)(*[self.eval_action(arg, env) for arg in a[1:]])

    def __init__(self, file):
        super(StateMachine, self).__init__()
        data = json.load(open(file, "r", encoding="utf8"))
        self.storage = data.pop("storage")
        self.resouces = data.pop("resources")
        self.states = data
        self.current_state = "start"
        self.timer = 0  # timer for animations
        self.anim = 0  # counter for animations
        self.key_events = {}
        self.env = std_env

        if "image" in self.resouces:
            for k, v in self.resouces["image"].items():
                if isinstance(v, str):
                    self.resouces["image"][k] = pyglet.image.load(r_path(v))
                elif isinstance(v, list):
                    # format for animations - ["file.png", cols, rows, time for each frame]
                    t_spritesheet = pyglet.image.load(r_path(v[0]))
                    t_tex = pyglet.image.TextureGrid(pyglet.image.ImageGrid(t_spritesheet, v[1], v[2]))
                    self.resouces["image"][k] = pyglet.image.Animation.from_image_sequence(t_tex, v[3])
        else:
            raise IndexError("No drawables detected!")

        if "sound" in self.resouces:
            for k, v in self.resouces["sound"].items():
                self.resouces["sound"][k] = Sound(r_path(v))
                self.resouces["sound"][k].set_volume(0.5)

        # initializing the images to the 'start' state
        s_state = self.states['start']['anim'][0]

        self.sprite = cocos.sprite.Sprite(self.resouces['image'][s_state['image']], (320, 180))
        eff = (s_state['effect'], s_state['time']) if 'effect' in s_state else None
        self.update_sprite(image=s_state['image'], effect=eff)
        self.label = cocos.text.Label(">", x=50, y=280)
        self.add(self.label)
        self.add(self.sprite)
        self.schedule(self.update)

    def get_state(self, state):
        if isinstance(state, list):
            return random.choices(*zip(*state))[0]
        else:
            return state

    def set_state(self, state):
        if state in self.states:
            self.current_state = state
            self.anim = 0
            self.timer = 0
            t_st = self.states[state]
            if t_st['anim']:
                t_st_a = t_st['anim'][0]
                img = t_st_a['image'] if 'image' in t_st_a else None
                eff = (t_st_a['effect'], t_st_a['time']) if 'effect' in t_st_a else None
                self.update_sprite(image=img, effect=eff)
                if 'sound' in t_st_a:
                    self.resouces['sound'][t_st_a['sound']].play(maxtime=round(t_st_a['time']*1000))
            if 'action' in t_st:
                for action in t_st['action']:
                    self.eval_action(action, self.env)

    def stop_sound(self, state, frame=-1):
        st_a = self.states[state]['anim']
        if st_a:
            if 0 <= frame < len(st_a) and 'sound' in st_a[frame]:
                self.resouces['sound'][st_a[frame]['sound']].stop()
            elif frame == -1:
                for f in st_a:
                    if 'sound' in f:
                        self.resouces['sound'][f['sound']].stop()

    def update_sprite(self, image=None, effect=None):
        if image:
            self.sprite.image = self.resouces['image'][image]
        if effect:
            if effect[0] == 'fade_in':
                self.sprite.do(FadeIn(effect[1]))
            elif effect[0] == 'fade_out':
                self.sprite.do(FadeOut(effect[1]))

    def update(self, dt):
        state = self.states[self.current_state]
        self.label.element.text = str(self.storage)

        # check how long the key events are running
        t_l = []
        for k in self.key_events.keys():
            self.key_events[k] -= dt
            if self.key_events[k] <= 0:
                t_l.append(k)

        for k in t_l:
            del self.key_events[k]

        # do animation
        limit = state['anim'][self.anim].get("time", 0)
        self.timer = min(self.timer + dt, limit)
        if "Z" in self.key_events or "X" in self.key_events:
            if "hit_any" in state['trans']:
                self.stop_sound(self.current_state)
                self.set_state(state['trans']['hit_any'])
                # self.current_state = self.get_state(state['trans']['hit_any'])
                # state = self.states[self.current_state]
                # self.anim = 0
                # self.sprite.image = self.resouces['image'][state['anim'][self.anim]['image']]
                # self.timer = 0
        if self.timer == limit:
            self.anim += 1
            if 'check' in state['trans']:
                for c in state['trans']['check']:
                    if self.eval_action(c[:-1], self.env):
                        self.set_state(self.get_state(c[-1]))
                        state = self.states[self.current_state]
                        break

            if self.anim >= len(state['anim']):
                if 'anim_end' in state['trans']:
                    self.set_state(self.get_state(state['trans']['anim_end']))
                    state = self.states[self.current_state]
                self.anim = 0
            img = state['anim'][self.anim]['image'] if 'image' in state['anim'][self.anim] else None
            eff = (state['anim'][self.anim]['effect'], state['anim'][self.anim]['time']) if 'effect' in state['anim'][self.anim] else None
            if 'sound' in state['anim'][self.anim]:
                print()
                self.resouces['sound'][state['anim'][self.anim]['sound']].play(maxtime=round(state['anim'][self.anim]['time']*1000))
            self.update_sprite(image=img, effect=eff)
            self.timer = 0

    def on_key_press(self, key, modifiers):
        k = pyglet.window.key.symbol_string(key)

        if not self.key_events and k in _BUTTONS:
            self.key_events[k] = 0.5


class FightState(StateMachine):
    """
    A class for loading and storing a fight state machine.
    states - a dict of different states that the machine goes through.
    storage - a dict of environment variables specific to the machine
    resources - a dict of resources the machine uses, for preloading.
    sprite - a Cocos2Dpy sprite (hopefully this works)
    key_events - a dict of key events like attacks and dodges/blocks
    """

    def __init__(self, file):
        super(FightState, self).__init__(file)
        self.env['fight_over'] = False
        self.env['hit'] = lambda *x: None
        self.dodgesprite = cocos.sprite.Sprite(self.resouces['image']['cube'], (320, 0))
        self.add(self.dodgesprite)

    def on_key_press(self, key, modifiers):
        k = pyglet.window.key.symbol_string(key)

        if not self.key_events and k in _BUTTONS:
            self.key_events[k] = 0.5
            act = MoveBy((0, 0), 0)
            if k == "LEFT":
                act = MoveBy((-50, 0), 0.25)
            elif k == "RIGHT":
                act = MoveBy((50, 0), 0.25)
            elif k == "Z":
                act = MoveBy((-20, 150), 0.1)
            elif k == "X":
                act = MoveBy((20, 150), 0.1)
            self.dodgesprite.do(act + Reverse(act))

    # def draw(self, *args, **kwargs):
        # self.sprite.draw()
        # self.dodgesprite.draw()


class KeyDisplay(cocos.layer.Layer):
    is_event_handler = True  #: enable pyglet's events

    def __init__(self):
        super(KeyDisplay, self).__init__()

        # sprite = cocos.sprite.Sprite(anim, (100, 100))
        #
        # self.add(sprite)
        self.fight = FightState('testfight.json')
        self.add(self.fight)

        self.text = cocos.text.Label("", x=100, y=280)

        # To keep track of which keys are pressed:
        self.keys_pressed = set()
        # self.update_text()
        self.add(self.text)
        self.schedule(self.update)

    def on_key_press(self, key, modifiers):
        self.fight.on_key_press(key, modifiers)

    def update(self, dt):
        if self.fight.env['fight_over']:
            cocos.director.director.replace(cocos.scene.Scene(KeyDisplay()))

    # def update_text(self):
    #     key_names = [pyglet.window.key.symbol_string(k) for k in self.keys_pressed]
    #     text = 'Keys: ' + ','.join(key_names)
    #     # Update self.text
    #     self.text.element.text = text
    #
    # def on_key_press(self, key, modifiers):
    #     """This function is called when a key is pressed.
    #
    #     'key' is a constant indicating which key was pressed.
    #     'modifiers' is a bitwise or of several constants indicating which
    #        modifiers are active at the time of the press (ctrl, shift, capslock, etc.)
    #
    #     See also on_key_release situations when a key press does not fire an
    #      'on_key_press' event.
    #     """
    #     self.keys_pressed.add(key)
    #     self.update_text()
    #
    # def on_key_release(self, key, modifiers):
    #     """This function is called when a key is released.
    #
    #     'key' is a constant indicating which key was pressed.
    #     'modifiers' is a bitwise or of several constants indicating which
    #        modifiers are active at the time of the press (ctrl, shift, capslock, etc.)
    #
    #     Constants are the ones from pyglet.window.key
    #
    #     Sometimes a key release can arrive without a previous 'press' event, so discard
    #     is used instead of remove.
    #
    #     This can happen in Windows by example when you 'press ALT, release ALT, press B,
    #     release B'; the events received are 'pressed ALT, released ALT, released B'.
    #
    #     This may depend on the pyglet version, here pyglet from repo at may 2014 was used.
    #     """
    #     self.keys_pressed.discard(key)
    #     self.update_text()


# class MouseDisplay(cocos.layer.Layer):
#     # If you want that your layer receives events
#     # you must set this variable to 'True',
#     # otherwise it won't receive any event.
#     is_event_handler = True
#
#     def __init__(self):
#         super(MouseDisplay, self).__init__()
#
#         self.posx = 100
#         self.posy = 240
#         self.text = cocos.text.Label('No mouse events yet', font_size=18, x=self.posx, y=self.posy)
#         self.add(self.text)
#
#     def update_text(self, x, y):
#         text = 'Mouse @ %d,%d' % (x, y)
#         self.text.element.text = text
#         self.text.element.x = self.posx
#         self.text.element.y = self.posy
#
#     def on_mouse_motion(self, x, y, dx, dy):
#         """Called when the mouse moves over the app window with no button pressed
#
#         (x, y) are the physical coordinates of the mouse
#         (dx, dy) is the distance vector covered by the mouse pointer since the
#           last call.
#         """
#         self.update_text(x, y)
#
#     def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
#         """Called when the mouse moves over the app window with some button(s) pressed
#
#         (x, y) are the physical coordinates of the mouse
#         (dx, dy) is the distance vector covered by the mouse pointer since the
#           last call.
#         'buttons' is a bitwise or of pyglet.window.mouse constants LEFT, MIDDLE, RIGHT
#         'modifiers' is a bitwise or of pyglet.window.key modifier constants
#            (values like 'SHIFT', 'OPTION', 'ALT')
#         """
#         self.update_text(x, y)
#
#     def on_mouse_press(self, x, y, buttons, modifiers):
#         """This function is called when any mouse button is pressed
#
#         (x, y) are the physical coordinates of the mouse
#         'buttons' is a bitwise or of pyglet.window.mouse constants LEFT, MIDDLE, RIGHT
#         'modifiers' is a bitwise or of pyglet.window.key modifier constants
#            (values like 'SHIFT', 'OPTION', 'ALT')
#         """
#         self.posx, self.posy = director.get_virtual_coordinates(x, y)
#         self.update_text(x, y)


if __name__ == "__main__":
    director.init(resizable=True)
    mixer.init()
    # Run a scene with our event displayers:
    director.run(cocos.scene.Scene(KeyDisplay()))
