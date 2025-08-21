from fastapi import APIRouter, Response
from midiutil import MIDIFile
import random
import io

router = APIRouter()

def generate_midi_bytes():
    midi = MIDIFile(2)
    tempo = 75
    volume = 85
    left_track = 0
    right_track = 1
    
    midi.addTrackName(left_track, 0, "Left Hand")
    midi.addTrackName(right_track, 0, "Right Hand")
    midi.addTempo(left_track, 0, tempo)
    midi.addTempo(right_track, 0, tempo)
    midi.addProgramChange(left_track, 0, 0, 0)
    midi.addProgramChange(right_track, 0, 1, 0)

    chords_left = [
        [57, 64],  # Am: A2, E3
        [53, 65],  # F: F2, A3
        [48, 60],  # C: C2, C3
        [55, 67]   # G: G2, G3
    ]

    chords_right = [
        [69, 72, 76, 79],  # Am7(9)
        [65, 69, 72, 77],  # Fmaj7
        [60, 64, 67, 71],  # Cmaj7
        [62, 67, 71, 74]   # G7
    ]

    progression_order = [0, 1, 2, 3]
    chord_duration = 4
    time_pointer = 0
    total_bars = 20

    for _ in range(total_bars):
        chord_idx = progression_order[time_pointer // chord_duration % len(progression_order)]

        left_notes = chords_left[chord_idx]
        left_time = time_pointer
        while left_time < time_pointer + chord_duration:
            note = random.choice(left_notes)
            octave_shift = random.choice([-12, 0])
            length = random.choice([1, 2])
            if left_time + length > time_pointer + chord_duration:
                length = time_pointer + chord_duration - left_time
            midi.addNote(left_track, 0, note + octave_shift, left_time, length, volume)
            left_time += length
        
        right_notes = chords_right[chord_idx][:]
        random.shuffle(right_notes)
        right_time = time_pointer
        while right_time < time_pointer + chord_duration:
            if not right_notes:
                right_notes = chords_right[chord_idx][:]
                random.shuffle(right_notes)
            note = right_notes.pop()
            length = random.choice([0.5, 1, 1.5])
            if right_time + length > time_pointer + chord_duration:
                length = time_pointer + chord_duration - right_time
            midi.addNote(right_track, 1, note, right_time, length, volume)
            right_time += length

        time_pointer += chord_duration

    buf = io.BytesIO()
    midi.writeFile(buf)
    buf.seek(0)
    return buf.read()

@router.get("/create-midi")
def create_midi():
    midi_bytes = generate_midi_bytes()
    return Response(content=midi_bytes, media_type="audio/midi")
