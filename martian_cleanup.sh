#target_ip=192.168.2.49
#target_ip=192.168
for pid in $(lsns -t net | tail -n +2 | awk '{print $4}'); do
  echo "Checking PID: $pid"
  sudo nsenter -t $pid -n bash -c '
    ip addr 2>&1;
    ip route 2>&1;
    iptables -S 2>&1;
    iptables -t nat -S 2>&1;
  ' | grep "155"
done;
