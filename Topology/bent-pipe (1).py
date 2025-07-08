"""
                          Simpilified "Bent-Pipe" topology for Starlink

               192.168.1.1/24                    100.64.0.1/10               10.10.10.101/24
User  -----------------------  Router  -----------------------  PoP  -----------------------  Dst
        192.168.1.101/24                 100.76.100.1/10               10.10.10.1/24

## Topology

User:
User device (e.g., laptop) connected to the Router.

Router:
The stock Starlink user router provisions a 192.168.1.0/24 network for end devices.

PoP:
Simplified PoP (Point of Presence) structure combined with landing ground stations.
In real Starlink networks, there is 1 IP-Hop between the user router to the PoP,
which traverses the User Dish, (potentially multiple) satellites, landing ground stations, and to the PoP.
For normal Starlink subscribers, CGNAT is utilized for IPv4, and the PoP / Gateway is always accessible at 100.64.0.1.
On the WAN side of the router, a address from 100.64.0.1/10 is assigned.

Dst:
In this topology, we simpilify the connectivity between PoP and destination server.
In real Starlink networks, network packets exit the PoP go through the IXP and transit to the destination server via terrestrial networks.

## Emulation

In this topology, we emulate the 15s latency handover pattern for the satellite link, i.e., the link between Router and PoP.
The latency and throughput traces are loaded from CSV files.
We assume the link between User and Router, and between PoP and Dst are stable and negligible.
"""

import csv
import time
import sched
import argparse
import threading
from collections import defaultdict

from mininet.cli import CLI
from mininet.net import Mininet
from mininet.log import setLogLevel
from mininet.link import TCLink

update_event = threading.Event()
latency_update_interval = 1

class NetworkConfigThread(threading.Thread):
    def __init__(self, net, host_name, dev, latency_trace=None):
        super().__init__()
        self.net = net
        self.host_name = host_name
        self.dev = dev
        self.latency = defaultdict(float)
        self.start_time = None
        if latency_trace:
            self.latency = self.load_latency_trace(latency_trace)

    def load_latency_trace(self, filename: str):
        data = defaultdict(float)
        with open(filename, "r") as csv_file:
            reader = csv.reader(csv_file)
            next(reader)
            for row in reader:
                data[float(row[1])] = float(row[2])
        return data

    def get_closest_latency(self) -> int:
        now_relative = time.time() - self.start_time
        closest = min(self.latency.keys(), key=lambda t: abs(t - now_relative))
        return int(self.latency[closest] / 2)

    def configureNetworkConditions(self):
        self.configureStaticNetworkConditions()
        max_updates = 10
        updates = 0
        while updates < max_updates:
            update_event.wait()
            delay = self.get_closest_latency()
            self.configureStaticNetworkConditions(delay=delay)
            update_event.clear()
            updates += 1

    def configureStaticNetworkConditions(self, delay=100, bw=100, loss=0):
        host = self.net.get(self.host_name)
        for intf in host.intfList():
            if intf.link and str(intf) == self.dev:
                a, b = intf.link.intf1, intf.link.intf2
                a.config(delay=f"{delay}ms", loss=loss)
                b.config(delay=f"{delay}ms", loss=loss)

    def run(self):
        self.start_time = time.time()
        scheduler = sched.scheduler(time.time, time.sleep)
        scheduler.enter(latency_update_interval, 1,
                        update_periodically,
                        (scheduler, self.start_time, latency_update_interval))
        threading.Thread(target=scheduler.run, daemon=True).start()
        self.configureNetworkConditions()

def update_periodically(scheduler, start_time, step):
    next_time = start_time + step
    sleep_time = next_time - time.time()
    if sleep_time > 0:
        update_event.set()
        scheduler.enter(sleep_time, 1,
                        update_periodically,
                        (scheduler, next_time, step))
    else:
        scheduler.enter(0, 1,
                        update_periodically,
                        (scheduler, time.time(), step))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='LEONetEM')
    parser.add_argument('--latency', type=str, help='Latency trace file in CSV format')
    args = parser.parse_args()

    if not args.latency:
        print("Please specify the latency trace file")
        exit(1)

    print(f"Using latency trace: {args.latency}")

    setLogLevel('info')
    net = Mininet(link=TCLink)

    user   = net.addHost('user')
    router = net.addHost('router')
    pop    = net.addHost('pop')
    dst    = net.addHost('dst')

    net.addLink(user,   router, cls=TCLink, bw=1000)
    net.addLink(router, pop,    cls=TCLink, bw=100, delay="100ms", loss=0)
    net.addLink(pop,    dst,    cls=TCLink, bw=1000)

    net.build()
    net.start()   # bring links up

    # User configuration
    user.cmd("ifconfig user-eth0 192.168.1.101 netmask 255.255.255.0 up")
    user.cmd("ip route add default via 192.168.1.1 dev user-eth0")
    user.cmd("ip route add 10.10.10.0/24 via 192.168.1.1 dev user-eth0")

    # Router configuration
    router.cmd("echo 1 > /proc/sys/net/ipv4/ip_forward")
    router.cmd("sysctl -w net.ipv4.conf.all.rp_filter=0")
    router.cmd("ifconfig router-eth0 192.168.1.1 netmask 255.255.255.0 up")
    router.cmd("ifconfig router-eth1 100.76.100.1 netmask 255.192.0.0 up")
    router.cmd("ip route add default via 100.64.0.1 dev router-eth1")
    router.cmd("ip route add 10.10.10.0/24 via 100.64.0.1 dev router-eth1")

    # PoP configuration
    pop.cmd("echo 1 > /proc/sys/net/ipv4/ip_forward")
    pop.cmd("sysctl -w net.ipv4.conf.all.rp_filter=0")
    pop.cmd("ifconfig pop-eth0 100.64.0.1 netmask 255.192.0.0 up")
    pop.cmd("ifconfig pop-eth1 10.10.10.1 netmask 255.255.255.0 up")
    pop.cmd("ip route add 192.168.1.0/24 via 100.76.100.1 dev pop-eth0")

    # Destination configuration
    dst.cmd("ifconfig dst-eth0 10.10.10.101 netmask 255.255.255.0 up")
    dst.cmd("ip route add default via 10.10.10.1 dev dst-eth0")

    # Populate direct-neighbor ARP entries
    net.staticArp()

    # Manually seed multi-hop ARP:
    # user → pop & dst via router-eth0
    r0 = router.MAC('router-eth0')
    user.cmd(f"arp -s 10.10.10.1   {r0}")
    user.cmd(f"arp -s 10.10.10.101 {r0}")
    # router → dst via pop-eth0
    p0 = pop.MAC('pop-eth0')
    router.cmd(f"arp -s 10.10.10.101 {p0}")
    # pop → user via router-eth1
    r1 = router.MAC('router-eth1')
    pop.cmd(f"arp -s 192.168.1.101 {r1}")

    """
    # Custom connectivity matrix test (ping -c1 -w3)
    print("\n*** Connectivity matrix test (ping -c1 -w3) ***")
    hosts = [user, router, pop, dst]
    for src in hosts:
        row = []
        for dst_h in hosts:
            if src is dst_h:
                row.append("–")
            else:
                out = src.cmd(f"ping -c1 -w3 {dst_h.IP()}")
                row.append("OK" if "1 received" in out else "FAIL")
        print(f"{src.name:6} ->  " + "  ".join(row))
    print()
    """
    
    # Start latency‐shaping thread
    net_thread = NetworkConfigThread(net, "router", "router-eth1", args.latency)
    net_thread.start()

    # Enter interactive CLI
    CLI(net)
