import mido
import threading
import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

HOME_ASSISTANT_URL = os.getenv('HOME_ASSISTANT_URL')
TOKEN = os.getenv('TOKEN')
LIGHT_ENTITY_ID = os.getenv('LIGHT_ENTITY_ID')

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def note_number_to_name(note_number):
    octave = note_number // 12 - 1
    note_name = NOTE_NAMES[note_number % 12]
    return f"{note_name}{octave}"

def change_light_color(color, brightness):
    url = f"{HOME_ASSISTANT_URL}/api/services/light/turn_on"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "entity_id": LIGHT_ENTITY_ID,
        "rgb_color": color,
        "brightness": brightness
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        print(f"Light color changed to {color} with brightness {brightness}")
    else:
        print(f"Failed to change light color: {response.text}")

def turn_off_light():
    url = f"{HOME_ASSISTANT_URL}/api/services/light/turn_off"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "entity_id": LIGHT_ENTITY_ID,
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        print("Light turned off")
    else:
        print(f"Failed to turn off light: {response.text}")

def midi_to_color(notes):
    if not notes:
        return [0, 0, 0]
    avg_note = sum(note['note'] % 12 for note in notes) // len(notes)
    red = (avg_note * 21) % 256
    green = (avg_note * 42) % 256
    blue = (avg_note * 84) % 256
    return [red, green, blue]

def calculate_brightness(notes):
    if not notes:
        return 0
    total_velocity = sum(note['velocity'] for note in notes)
    num_notes = len(notes)
    # Adjust brightness to be higher with more keys pressed and scaled by velocity
    # Scale brightness so that it reaches maximum value when more than 6 keys are pressed
    brightness = int((total_velocity / (num_notes * 127)) * 255 * (num_notes/1.5 ))
    print(f"Total velocity: {total_velocity}, num notes: {num_notes}, brightness: {brightness}")
    # Cap brightness at 255
    return min(brightness, 255)

def check_notes_state():
    global pressed_notes
    current_time = time.time()
    pressed_notes = [note for note in pressed_notes if current_time - note['timestamp'] < 0.1]  # 2 seconds interval
    if not pressed_notes:
        print("No notes pressed (timer check)")
        turn_off_light()
    threading.Timer(0.1, check_notes_state).start()  # Check again after 1 second

def main():
    global pressed_notes
    pressed_notes = []
    port_name = mido.get_input_names()[0]
    with mido.open_input(port_name) as port:
        print(f"Listening to MIDI input on {port_name}")
        check_notes_state()  # Start the periodic check
        for message in port:
            current_time = time.time()

            if message.type == 'note_on' and message.velocity > 0:
                note = message.note
                velocity = message.velocity
                pressed_notes.append({'note': note, 'velocity': velocity, 'timestamp': current_time})
                current_notes = sorted(pressed_notes, key=lambda x: x['note'])
                note_names = [note_number_to_name(n['note']) for n in current_notes]
                velocities = [n['velocity'] for n in current_notes]
                color = midi_to_color(current_notes)
                brightness = calculate_brightness(current_notes)
                print(f"Pressed notes: {note_names} with velocities {velocities} (color: {color}, brightness: {brightness})")
                change_light_color(color, brightness)
            elif message.type == 'note_off' or (message.type == 'note_on' and message.velocity == 0):
                note = message.note
                pressed_notes = [n for n in pressed_notes if n['note'] != note]

if __name__ == '__main__':
    main()
