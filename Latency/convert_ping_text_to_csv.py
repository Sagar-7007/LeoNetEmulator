import csv
from datetime import datetime

def convert_to_csv(input_txt: str, output_csv: str):
    timestamps = []
    rtts = []

    with open(input_txt, 'r') as infile:
        lines = infile.readlines()

        # Skip the first header line
        for line in lines[1:]:
            if not line.strip():
                continue
            try:
                ts_str, rtt_str = line.strip().split(',')
                ts = datetime.strptime(ts_str.strip(), "%Y-%m-%d %H:%M:%S.%f")
                rtt = float(rtt_str.strip())
                timestamps.append(ts)
                rtts.append(rtt)
            except Exception as e:
                print(f"Skipping line due to error: {line.strip()} ({e})")

    if not timestamps:
        print("No valid data found.")
        return

    base_time = timestamps[0]

    with open(output_csv, 'w', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=["timestamp", "relative", "rtt"])
        writer.writeheader()
        for ts, rtt in zip(timestamps, rtts):
            relative_sec = (ts - base_time).total_seconds()
            writer.writerow({
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "relative": f"{relative_sec:.3f}",
                "rtt": rtt
            })

    print(f"Converted data written to {output_csv}")

# Example usage:
convert_to_csv("ping_sample.txt", "ping_sample.csv")
