"""Spoof job data that would come from JIRA"""
from run import Job
from datetime import timedelta
from random import choice

spoof_descs = [
    "Get rid of databases and import everything into CSVs so that nothing ever crashes",
    "The company car needs washing.",
    "Need to add a new user to JIRA.",
    "Re-write fused-batchnorms in tf.keras so that is_training ACTUALLY works when you freeze it.",
]

spoof_times = [
    timedelta(days=3, minutes=45, seconds=18),
    timedelta(days=0, minutes=45, seconds=0),
    timedelta(days=0, minutes=10, seconds=15),
    timedelta(days=15, minutes=2, seconds=42),
]

SPOOF_JOBS = [
        Job('DE-1132', spoof_descs[0], spoof_times[0]),
        Job('ZD-8913', spoof_descs[1], spoof_times[1]),
        Job('JI-1121', spoof_descs[2], spoof_times[2]),
        Job('KR-7613', spoof_descs[3], spoof_times[3]),
]

# extend with random mixes
for i in range (5):
    SPOOF_JOBS.append(Job('ZJ-{}000'.format(i) , choice(spoof_descs), choice(spoof_times)))
