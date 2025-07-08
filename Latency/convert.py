import os
import sys
import csv
import time
from pathlib import Path
from multiprocessing import Pool
from util import load_ping


csv_dir = "./"
raw_dir = "./"


def convert_ping_csv(file_path: str) -> None:
    print(file_path)
    outfile_path = Path(str(file_path).replace(raw_dir, csv_dir))
    if os.path.isfile(outfile_path.with_suffix(".csv")):
        return
    v_ping = load_ping(file_path)
    if v_ping == None:
        print("error: ", file_path)
        sys.exit(1)
    init_time = v_ping.ts[0]
    with open(outfile_path.with_suffix(".csv"), 'w', newline='') as outcsv:
        writer = csv.DictWriter(outcsv, fieldnames = ["timestamp", "relative", "rtt"])
        writer.writeheader()

        writer.writerows({"timestamp": v_ping.ts[i], "relative": v_ping.ts[i] - init_time , "rtt": v_ping.rtt[i]} for i in range(len(v_ping.ts)))


if __name__ == "__main__":
    p = Pool(2)
    ping_job = []

    path = Path(raw_dir)
    for dirpath, dirnames, files in os.walk(path):
        if len(files) != 0:
            for f in files:
                if f.endswith(".txt") and f.startswith("ping"):
                    ping_job.append(str(Path(dirpath).joinpath(f)))

    ping_job.sort(key=str.lower)
    start = time.time()
    p.map(convert_ping_csv, ping_job)
    print("{} seconds elapsed".format(time.time() - start))
