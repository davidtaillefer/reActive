from .laps import assign_records_to_laps, assign_lengths_to_laps
from .grades import compute_and_smooth_grades, extract_activity_climbs, grade_stats

def finalize_activity(activity):
    assign_records_to_laps(activity.track, activity.laps)
    if activity.lengths:
        assign_lengths_to_laps(activity.lengths, activity.laps)

    compute_and_smooth_grades(activity.track)
    extract_activity_climbs(activity, termination_buffer_m=200)
    
    # activity.grade_min, activity.grade_max = grade_stats(activity.track)

    return activity