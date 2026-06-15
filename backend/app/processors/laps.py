
def assign_records_to_laps(records, laps):
    lap_idx = 0

    for r in records:
        while lap_idx < len(laps) and r.timestamp >= laps[lap_idx].end_time:
            lap_idx += 1

        if lap_idx < len(laps):
            lap = laps[lap_idx]
            if lap.start_time <= r.timestamp < lap.end_time:
                lap.track.append(r)
                
def assign_lengths_to_laps(lengths, laps):
    for lap in laps:
        first_length_index = lap.first_length_index
        num_lengths = lap.num_lengths
        # print(f"Lap {lap.lap_id} numlengths {num_lengths} {first_length_index}")
        if num_lengths == 0:
            num_lengths = 1
        for i in range(0, num_lengths):
            # print(f"Lap {lap.lap_id} Length {i+first_length_index}")
            lap.lengths.append(lengths[i + first_length_index])
