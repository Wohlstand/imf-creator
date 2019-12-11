from enum import IntEnum
from functools import total_ordering


class EventType(IntEnum):
    """Song event types.

    Data dictionary for each type:
     * NOTE_OFF: "note", "velocity"
     * NOTE_ON: "note", "velocity"
     * POLYPHONIC_KEY_PRESSURE: "note", "pressure"
     * CONTROLLER_CHANGE: "controller", "value"
     * PROGRAM_CHANGE: "program"
     * CHANNEL_KEY_PRESSURE: "pressure"
     * PITCH_BEND: "value" from -1.0 to 1.0 where 0 = center.  Bend by current bend amount.
     * F0_SYSEX: "bytes"
     * F7_SYSEX: "bytes"
     * META: See MetaType
    """
    NOTE_OFF = 0x80
    NOTE_ON = 0x90
    POLYPHONIC_KEY_PRESSURE = 0xa0
    CONTROLLER_CHANGE = 0xb0  # Also has channel mode messages.
    PROGRAM_CHANGE = 0xc0
    CHANNEL_KEY_PRESSURE = 0xd0
    PITCH_BEND = 0xe0
    F0_SYSEX = 0xf0
    F7_SYSEX = 0xf7
    META = 0xff


@total_ordering
class SongEvent:
    """Represents a song event.
    This is pretty much just a MIDI event and song readers should convert their file format's events to match MIDI.

    The data dictionary will vary per event_type.  See EventType.
    """

    def __init__(self, track: int, time: float, event_type: "EventType", data: dict = None, channel: int = None):
        """Creates a song event.

        :param track: The track number for the event.
        :param time: The time of the event from the start of the song, in beats.
        :param event_type: The event type.
        :param data: A data dictionary for the event.  Contents will vary per event_type.
        :param channel: The event channel.  Must be None for sysex and meta event types and an integer for all others.
        """
        # Validate arguments.
        if event_type in [EventType.F0_SYSEX, EventType.F7_SYSEX, EventType.META]:
            if channel is not None:
                raise ValueError(f"Channel must be None for {event_type} events.")
        elif channel is None or type(channel) is not int:
            raise ValueError(f"Channel must be an integer for {event_type} events.")
        if event_type == EventType.META and "meta_type" not in data:
            raise ValueError(f"{event_type} events must have a 'meta_type' data entry.")
        # Set fields.
        self.track = track
        self.time = time
        self.type = event_type
        self._data = data
        self.channel = channel

    def __repr__(self):
        text = f"{self.time:0.3f}: {str(self.type)}"
        if self.type == EventType.META:
            text += f" - {str(self._data['meta_type'])}"
        elif self.channel is not None:
            text += f" - {self.channel}"
        return f"[{text} - {self._data}]"

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __eq__(self, other: "SongEvent"):
        if self.time != other.time:
            return False
        if _EVENT_TYPE_ORDER[self.type] != _EVENT_TYPE_ORDER[other.type]:
            return False
        # if self.channel != other.channel:
        #     return False
        if self.track != other.track:
            return False
        return True

    def __lt__(self, other: "SongEvent"):
        if self.time < other.time:
            return True
        elif self.time > other.time:
            return False
        if _EVENT_TYPE_ORDER[self.type] < _EVENT_TYPE_ORDER[other.type]:
            return True
        elif _EVENT_TYPE_ORDER[self.type] > _EVENT_TYPE_ORDER[other.type]:
            return False
        # if self.channel < other.channel:
        #     return True
        # elif self.channel > other.channel:
        #     return False
        return self.track < other.track


class MetaType(IntEnum):
    """Song meta event types.
    Not all meta types are used by the conversion process.

    Data dictionary for each meta type:
     * SEQUENCE_NUMBER: "number"
     * TEXT_EVENT: "text"
     * COPYRIGHT: "text"
     * TRACK_NAME: "text"
     * INSTRUMENT_NAME: "text"
     * LYRIC: "text"
     * MARKER: "text"
     * CUE_POINT: "text"
     * PROGRAM_NAME: "text"
     * DEVICE_NAME: "text"
     * CHANNEL_PREFIX: "channel" 0..15
     * PORT: "port" 0..127
     * END_OF_TRACK: None
     * SET_TEMPO: "bpm"
     * SMTPE_OFFSET: "hours", "minutes", "seconds", "frams", "fractional_frames"
     * TIME_SIGNATURE: "numerator", "denominator", "midi_clocks_per_metronome_tick", "number_of_32nd_notes_per_beat"
     * KEY_SIGNATURE: "key"  # should reflect major/minor, A vs Am
     * SEQUENCER_SPECIFIC: "bytes"
    """
    SEQUENCE_NUMBER = 0x00,
    TEXT_EVENT = 0x01,
    COPYRIGHT = 0x02,
    TRACK_NAME = 0x03,
    INSTRUMENT_NAME = 0x04,
    LYRIC = 0x05,
    MARKER = 0x06,
    CUE_POINT = 0x07,
    PROGRAM_NAME = 0x08,
    DEVICE_NAME = 0x09,
    CHANNEL_PREFIX = 0x20,
    PORT = 0x21,
    END_OF_TRACK = 0x2f,
    SET_TEMPO = 0x51,
    SMTPE_OFFSET = 0x54,
    TIME_SIGNATURE = 0x58,
    KEY_SIGNATURE = 0x59,
    SEQUENCER_SPECIFIC = 0x7f,


_EVENT_TYPE_ORDER = {
    EventType.NOTE_OFF: 10,
    EventType.NOTE_ON: 100,
    EventType.POLYPHONIC_KEY_PRESSURE: 40,
    EventType.CONTROLLER_CHANGE: 1,  # Controller changes are high priority, just lower than program change.
    EventType.PROGRAM_CHANGE: 0,  # Program changes are high priority.
    EventType.CHANNEL_KEY_PRESSURE: 50,
    EventType.PITCH_BEND: 30,
    EventType.F0_SYSEX: 0,  # Ignored, order doesn't matter.
    EventType.F7_SYSEX: 0,  # Ignored, order doesn't matter.
    EventType.META: 0,  # Tempo changes, for example, should be high priority.
}


class ControllerType(IntEnum):
    """MIDI controller type codes."""
    BANK_SELECT_MSB = 0,  # Allows user to switch bank for patch selection. Program change used with Bank Select.
                          # MIDI can access 16,384 patches per MIDI channel.
    MODULATION_WHEEL_MSB = 1,  # Generally this CC controls a vibrato effect (pitch, loudness, brighness).
                               # What is modulated is based on the patch.
    BREATH_CONTROLLER_MSB = 2,  # Often times associated with aftertouch messages. It was originally intended for use
                                # with a breath MIDI controller in which blowing harder produced higher MIDI control
                                # values. It can be used for modulation as well.
    # 3 is undefined
    FOOT_CONTROLLER_MSB = 4,  # Often used with aftertouch messages. It can send a continuous stream of values based on
                              # how the pedal is used.
    PORTAMENTO_TIME_MSB = 5,  # Controls portamento rate to slide between 2 notes played subsequently.
    DATA_ENTRY_MSB = 6,  # Controls Value for NRPN or RPN parameters.
    VOLUME_MSB = 7,  # Control the volume of the channel
    BALANCE_MSB = 8,  # Controls the left and right balance, generally for stereo patches.
                      # 0 = hard left, 64 = center, 127 = hard right
    # 9 is undefined
    PAN_MSB = 10,  # Controls the left and right balance, generally for mono patches.
                   # 0 = hard left, 64 = center, 127 = hard right
    EXPRESSION_MSB = 11,  # Expression is a percentage of volume (CC7).
    EFFECT_1_MSB = 12,  # Usually used to control a parameter of an effect within the synth/workstation.
    EFFECT_2_MSB = 13,  # Usually used to control a parameter of an effect within the synth/workstation.
    # 14-15 are undefined
    GENERAL_PURPOSE_1_MSB = 16,
    GENERAL_PURPOSE_2_MSB = 17,
    GENERAL_PURPOSE_3_MSB = 18,
    GENERAL_PURPOSE_4_MSB = 19,
    # 20-31 are undefined
    BANK_SELECT_LSB = 32,
    MODULATION_LSB = 33,
    BREATH_CONTROLLER_LSB = 34,
    # 35 is undefined
    FOOT_CONTROLLER_LSB = 36,
    PORTAMENTO_TIME_LSB = 37,
    DATA_ENTRY_LSB = 38,
    VOLUME_LSB = 39,
    BALANCE_LSB = 40,
    # 41 is undefined
    PAN_LSB = 42,
    EXPRESSION_LSB = 43,
    EFFECT_1_LSB = 44,
    EFFECT_2_LSB = 45,
    # 46-47 are undefined
    GENERAL_PURPOSE_1_LSB = 48,
    GENERAL_PURPOSE_2_LSB = 49,
    GENERAL_PURPOSE_3_LSB = 50,
    GENERAL_PURPOSE_4_LSB = 51,
    # 52-63 are undefined
    SUSTAIN_PEDAL_SWITCH = 64,  # On/Off switch that controls sustain. (See also Sostenuto CC 66)
                                # 0-63 = Off, 64-127 = On
    PORTAMENTO_SWITCH = 65,  # On/Off switch 0 to 63 = Off, 64 to 127 = On
    SOSTENUTO_SWITCH = 66,  # On/Off switch – Like the Sustain controller (CC 64), However it only holds notes that
                            # were “On” when the pedal was pressed. People use it to “hold” chords” and play melodies
                            # over the held chord.  0 to 63 = Off, 64 to 127 = On
    SOFT_PEDAL_SWITCH = 67,  # On/Off switch - Lowers the volume of notes played. 0 to 63 = Off, 64 to 127 = On
    LEGATO_FOOTSWITCH = 68,  # On/Off switch - Turns Legato effect between 2 subsequent notes On or Off.
                             # 0 to 63 = Off, 64 to 127 = On
    HOLD_2_SWITCH = 69,  # Another way to “hold notes” (see MIDI CC 64 and MIDI CC 66). However notes fade out
                         # according to their release parameter rather than when the pedal is released.
    SOUND_CONTROLLER_1 = 70,  # Usually controls the way a sound is produced. Default = Sound Variation.
    SOUND_CONTROLLER_2 = 71,  # Allows shaping the Voltage Controlled Filter (VCF). Default = Resonance
    SOUND_CONTROLLER_3 = 72,  # Controls release time of the Voltage controlled Amplifier (VCA). Default = Release Time
    SOUND_CONTROLLER_4 = 73,  # Controls the “Attack’ of a sound.
    SOUND_CONTROLLER_5 = 74,  # Controls VCFs cutoff frequency of the filter.
    SOUND_CONTROLLER_6 = 75,
    SOUND_CONTROLLER_7 = 76,
    SOUND_CONTROLLER_8 = 77,
    SOUND_CONTROLLER_9 = 78,
    SOUND_CONTROLLER_10 = 79,
    GENERAL_PURPOSE_5 = 80,  # Generic On/Off switch, 0 to 63 = Off, 64 to 127 = On
    GENERAL_PURPOSE_6 = 81,  # Generic On/Off switch, 0 to 63 = Off, 64 to 127 = On
    GENERAL_PURPOSE_7 = 82,  # Generic On/Off switch, 0 to 63 = Off, 64 to 127 = On
    GENERAL_PURPOSE_8 = 83,  # Generic On/Off switch, 0 to 63 = Off, 64 to 127 = On
    PORTAMENTO_AMOUNT = 84,
    # 85-90 are undefined
    EFFECTS_1_DEPTH = 91,  # Usually controls reverb send amount
    EFFECTS_2_DEPTH = 92,  # Usually controls tremolo amount
    EFFECTS_3_DEPTH = 93,  # Usually controls chorus amount
    EFFECTS_4_DEPTH = 94,  # Usually controls detune amount
    EFFECTS_5_DEPTH = 95,  # Usually controls phaser amount
    DATA_INCREMENT = 96,  # Usually used to increment data for RPN and NRPN messages.
    DATA_DECREMENT = 97,  # Usually used to decrement data for RPN and NRPN messages.
    NRPN_LSB = 98,  # For controllers 6, 38, 96, and 97 it selects the NRPN parameter.
    NRPN_MSB = 99,  # For controllers 6, 38, 96, and 97 it selects the NRPN parameter.
    RPN_LSB = 100,  # For controllers 6, 38, 96, and 97 it selects the RPN parameter.
    RPN_MSB = 101,  # For controllers 6, 38, 96, and 97 it selects the RPN parameter.
    # 102-119 are undefined
    ALL_SOUND_OFF = 120
    RESET_ALL_CONTROLLERS = 121
    LOCAL_ON_OFF_SWITCH = 122
    ALL_NOTES_OFF = 123
    OMNI_MODE_OFF = 124
    OMNI_MODE_ON = 125
    MONOPHONIC_MODE = 126
    POLYPHONIC_MODE = 127
