from scapy.all import rdpcap, IP, ICMP
import matplotlib.pyplot as plt
import pandas as pd
import csv

# === Step 1: Load the pcap file ===
pcap_file = "icmp_user.pcap"
packets = rdpcap(pcap_file)

# === Step 2: Extract Echo Requests and Replies ===
echo_requests = []
echo_replies = []

for pkt in packets:
    if IP in pkt and ICMP in pkt:
        icmp = pkt[ICMP]
        if icmp.type == 8:  # Echo Request
            echo_requests.append((icmp.id, icmp.seq, pkt.time))
        elif icmp.type == 0:  # Echo Reply
            echo_replies.append((icmp.id, icmp.seq, pkt.time))

# === Step 3: Match request-reply and calculate RTT ===
rtts = []
for req_id, req_seq, req_time in echo_requests:
    for i, (rep_id, rep_seq, rep_time) in enumerate(echo_replies):
        if rep_id == req_id and rep_seq == req_seq:
            rtt_ms = (rep_time - req_time) * 1000  # convert to milliseconds
            if 0 < rtt_ms < 10000:  # filter valid RTTs
                rtts.append((req_time, rtt_ms))
            del echo_replies[i]  # prevent double-matching
            break

# === Step 4: Print sample count and save CSV ===
print(f"✅ Found {len(rtts)} RTT samples")
if len(rtts) == 0:
    print("⚠️ No valid RTT samples found.")
    exit()

with open("icmp_rtts.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Timestamp", "RTT (ms)"])
    writer.writerows(rtts)
print("📄 RTT data saved to icmp_rtts.csv")

# === Step 5: Create dataframe and plot ===
df = pd.DataFrame(rtts, columns=["Timestamp", "RTT (ms)"])
df["Time (s)"] = df["Timestamp"] - df["Timestamp"].min()

plt.figure(figsize=(12, 6))
plt.plot(df["Time (s)"], df["RTT (ms)"], color='mediumblue', linewidth=1)
plt.title("ICMP Round-Trip Time (RTT)")
plt.xlabel("Time (s)")
plt.ylabel("RTT (ms)")
plt.grid(True)
plt.tight_layout()

# === Step 6: Save the graph ===
plt.savefig("icmp_rtt_plot.png", dpi=300)
print("📊 Plot saved as icmp_rtt_plot.png")

# === Optional: Show plot interactively ===
plt.show()
