# Proxy Gateway for OpenValidators

## Summary
This repository contains the code for a proxy that acts as a gateway on the validator side.
The goal is to prevent requests made on the API server from being rejected on miners side. 
This happens because their IPs are not in the whitelist and miners have set up firewalls against DDoS attacks.
The solution is to setup a proxy on the validator side (acting as a gateway between API server and the miner) to use the validator IP which is registered.

## General Overview
- Pin a `tunnel` on Cloudflare for the secure connection between the validator and the API server.
- Setup the proxy on the validator server and configure the proxy.
- Run cloudflare daemon (`cloudflared`) on API server to query the network through the validator.

## Prerequisites
- Domain on Cloudflare for the proxy
- Validator server registered on the network
- API server serving any kind of API that requires access to the network
- Proxy that supports `connect` method


## Step-by-step Guide

1. Create a Cloudflare tunnel [More...](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/install-and-setup/tunnel-guide/remote/)

2. Install `cloudflared` on validator server [More...](https://pkg.cloudflare.com/index.html)
    (In my case, I'm using Ubuntu 22.04)
    #### Add cloudflare gpg key
    ```bash
    sudo mkdir -p --mode=0755 /usr/share/keyrings
    curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
    ```

    #### Add this OS Cloudflare package repo to your apt repositories
    ```bash
    echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared jammy main' | sudo tee /etc/apt/sources.list.d/cloudflared.list
    ```

    #### Install `cloudflared`
    ```bash
    sudo apt-get update && sudo apt-get install cloudflared
    ```

    #### Check if `cloudflared` is installed successfully (should show veresion number)
    ```bash
    cloudflared -V
    ```

    #### Run `cloudflared tunnel`
    ```bash
    pm2 start "cloudflared tunnel run --token <YOUR-TUNNEL-TOKEN>" --name cloudflared
    ```

3. Install `cloudflared` on API server
    (In my case, I'm using Ubuntu 22.04)
    #### Download `*.deb` file from GitHub
    ```bash
    curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
    ```

    #### Install `cloudflared`
    ```basb
    sudo dpkg -i cloudflared.deb
    ```

    #### Connect to Cloudflare Tunnel
    ```bash
    pm2 start cloudflared -- access tcp --hostname <YOUR-DOMAIN> --url localhost:8888
    ```

4. Install proxy on validator server
    #### Install Go
    ```bash
    wget https://go.dev/dl/go1.21.0.linux-amd64.tar.gz
    rm -rf /usr/local/go && tar -C /usr/local -xzf go1.21.0.linux-amd64.tar.gz
    export PATH=$PATH:/usr/local/go/bin
    ```

    #### Clone the proxy code from Github
    ```bash
    git clone git@github.com:adriansmares/connect.git
    ```

    #### Run proxy code
    ```bash
    cd connect
    pm2 start --name connect go -- run main.go
    ```

5. Start API server (via `cloudflared`)
```bash
grpc_proxy=http://localhost:8888 pm2 start python --name api -- main.py
```
