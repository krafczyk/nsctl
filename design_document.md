# Purpose

`nnsctl` is meant to set up network namespaces that are connected to the host network. Network traffic should be routed to the host network namespace, before arriving at the NIC and internet. applications launched within the namespace will only modify network settings of their specific namespace. Applications launched within should be able to specify the IP of the host network to interact with network applications such as X windows or another server which exists on the host. `nnsctl` will help launching VPNs as well so those VPNs can be isolated within the namespace. Once a VPN has been created, applications launched within the network namespace should both be able to interact with the internet through the VPN along with host servers like X.

## Specific Requirements

* `nnsctl --help`: Print argument help documentation
* `nnsctl --version`: Print version information
* `nnsctl list`: list network namespaces set up or managed by nnsctl.
* `nnsctl create <ns_name> [--host-subnet <subnet>] [--host-if <if>] [--ns-subnet <subnet>]`: Create a network namespace. Creates a pair of virtual interfaces and moves one into the newly created namespace. By default, the application attempts to detect the host's ip/subnet, but this application can accept the `--host-subnet` argument so it can be directly specified. Additionally, the application tries to automatically create a valid new subnet for the new namespace, but we can accept the `--ns-subnet` option to set it explicitly. Routing rules are added to the route table to automatically direct traffic arriving at the host from the new namespace to the host's active interface for internet connections. The application attempts to guess this, but it can be specified explicitly with `--host-if`. These settings are copied into a `/tmp/nnsctl/<ns_name>/configuration.conf` configuration file, so they can be used in later commands. 
* `nnsctl destroy <ns_name> [--force]`: Check for applications running within the network namespace. If applications are running, list them and abort. If `--force` is specified kill these applications and then tear down the interfaces, and rules associated with it.
* `nnsctl status <ns_name>`: Report the status of a particular network namespace, Should list whether a network namespace exists with the given name, and which interfaces are associated with the namespace, and routing table rules.
* `nnsctl exec <ns_name> <command>`: Launches a program inside the `ns_name` namespace.
* `nnsctl forward-port <ns_name> <port>`: Adds routing and masquerade rules inside and outside `ns_name` to send traffic destined to a particular port inside the network namespace to the same port in the host namespace. Thus inside the namespace, `localhost:<port>` is automatically connected to the server running in the host namespace on port `<port>`, and the user doesn't have to change ip address configuration for needed applications.
* `nnsctl forward-x <ns_name>`: Specialization of `nnsctl forward-port` for the x server, This just uses 6000 as the port.

## Example workflows

### Run matlab server requiring keyserver licensing where keyserver is only available on VPN

```bash
nnsctl create matlab_nns
nnsctl exec matlab_nns openconnect <openconnect options for university> 
# Wait until vpn is started
nnsctl forward-x matlab_nns # allow x connections to use `localhost`, this can be run in another terminal as well.
nnsctl forward-port matlab_nns 12345 # forward port 12345 served by the matlab application to the host. Traffic sent to this port from the host is transferred into the matlab_nns namespace and sent to the matlab server seamlessly.
nnsctl exec matlab_nns matlab # GUI appears seamlessly on host, and server starts. can be run in another terminal
python client_app.py --server localhost:12345 # python client application connects to the matlab server as if it's running locally, traffic is directed into the namespace automatically.
# After client is finished, close matlab server as appropriate
# either kill or Ctrl+C openconnect
nnsctl destroy matlab_nns # Removes all routing/interfaces associated with this namespace.
```

### Connect to HPC server within a VPN with restricted access using ssh while allowing X forwarding

```bash
nnsctl create restricted_nns
nnsctl exec restricted_nns openconnect <openconnect options for restricted network> # this can be run in another terminal as well.
# Wait until vpn is started
nnsctl forward-x restricted_nns # allow x connections to use `localhost`
nnsctl exec restricted_nns ssh <username>@<restricted_server_name_or_ip> -XY # x applications appear on host X server w/o changing settings
ping google.com # goes through main ethernet connection
nnsctl exec restricted_nns ping google.com # goes through VPN
# either kill or Ctrl+C openconnect
nnsctl destroy restricted_nns # Removes all routing/interfaces associated with this namespace.
```

### Run torrent utility within a nns while preserving regular network operation

```bash
nnsctl create torrent_nns
nnsctl exec torrent_nns expressvpn connect <site> # User launches expressvpn as they normally would but inside the namespace, this can be run in another terminal as well.
# Wait until vpn is started
nnsctl forward-x torrent_nns # allow x connections to use `localhost`
nnsctl exec torrent_nns qbittorrent # GUI lanches without intervention on host, internet traffic leaves through VPN
# either kill, ctrl+c, or otherwise shutdown expressvpn
nnsctl destroy torrent_nns
```
