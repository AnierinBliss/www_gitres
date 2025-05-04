#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2025 The Evolution X Project
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import requests
import json

def print_error(message):
    print(f"\033[91m{message}\033[0m")

def fetch_branches(github_token):
    base_headers = {"Authorization": f"token {github_token}"}
    print("Fetching branches...")
    response = requests.get(
        "https://api.github.com/repos/Evolution-X/OTA/branches", headers=base_headers
    )
    if response.status_code != 200:
        print_error("Error: Failed to fetch branch data.")
        sys.exit(1)

    branches = [branch["name"] for branch in response.json()]
    if not branches:
        print_error("No branches found.")
        sys.exit(1)

    print("\nBranches found:")
    for branch in branches:
        print(f"- {branch}")

    return branches

def fetch_maintainers_for_device(device_filename, branch, github_token):
    url = f"https://raw.githubusercontent.com/Evolution-X/OTA/refs/heads/{branch}/builds/{device_filename}"
    response = requests.get(url, headers={"Authorization": f"token {github_token}"})

    if response.status_code != 200:
        print_error(f"Failed to fetch JSON for {device_filename} on branch {branch}. "
                    f"Status code: {response.status_code}")
        return []

    try:
        content = response.json()
    except requests.exceptions.JSONDecodeError as e:
        print_error(f"Error decoding JSON for {device_filename} on branch {branch}: {e}")
        return []

    if not content or "response" not in content or not content["response"]:
        print_error(f"No maintainer entries for {device_filename} on branch {branch}.")
        return []

    entries = []
    for m in content["response"]:
        github_username = m.get("github")
        maintainer_name = m.get("maintainer")
        oem = m.get("oem")
        device_name = m.get("device")
        maintained = m.get("currently_maintained", False)
        if github_username and maintainer_name and oem and device_name:
            entries.append((maintainer_name, github_username, oem, device_name, maintained))
    return entries

def main():
    if len(sys.argv) != 2:
        print_error("Usage: ./update_maintainers.py <GITHUB_TOKEN>")
        sys.exit(1)

    github_token = sys.argv[1]
    branches = fetch_branches(github_token)
    current_maintainers_data = {}
    previous_maintainers_data = {}

    if os.path.exists("maintainers.json"):
        with open("maintainers.json", "r") as f:
            try:
                existing_data = json.load(f)
                for maintainer in existing_data.get("active_maintainers", []) + existing_data.get("inactive_maintainers", []):
                    previous_maintainers_data[maintainer["name"]] = {
                        "github": maintainer["github"],
                        "currently_maintains": set(maintainer.get("currently_maintains", [])),
                        "used_to_maintain": set(maintainer.get("used_to_maintain", [])),
                    }
            except json.JSONDecodeError:
                print_error("Warning: Could not decode existing maintainers.json. Starting fresh.")

    for branch in branches:
        print(f"\nProcessing branch: {branch}")
        url = f"https://api.github.com/repos/Evolution-X/OTA/contents/builds?ref={branch}"
        resp = requests.get(url, headers={"Authorization": f"token {github_token}"})
        if resp.status_code != 200:
            print_error(f"Error fetching device list for branch {branch}.")
            continue

        device_files = [
            item["name"]
            for item in resp.json()
            if item["name"].endswith(".json")
        ]
        if not device_files:
            print(f"No devices found on branch {branch}.")
            continue

        for device_filename in device_files:
            print(f"  Fetching {device_filename} …")
            entries = fetch_maintainers_for_device(device_filename, branch, github_token)
            device_key = None
            current_maintainers_on_device_branch = set()
            codename = os.path.splitext(device_filename)[0]
            for name, github_user, oem, dev, is_active in entries:
                device_key = f"{oem} {dev}"
                current_maintainers_on_device_branch.add(name)
                if name not in current_maintainers_data:
                    current_maintainers_data[name] = {
                        "github": github_user,
                        "currently_maintains": set(),
                        "used_to_maintain": set(),
                    }
                if is_active:
                    current_maintainers_data[name]["currently_maintains"].add(codename)
                    if codename in current_maintainers_data[name]["used_to_maintain"]:
                        current_maintainers_data[name]["used_to_maintain"].remove(codename)
                else:
                    if codename not in current_maintainers_data[name]["currently_maintains"]:
                        current_maintainers_data[name]["used_to_maintain"].add(codename)

            if device_key and branch in branches:
                previous_maintainers_for_device = {}
                for prev_name, prev_data in previous_maintainers_data.items():
                    if codename in prev_data.get("currently_maintains", set()):
                        previous_maintainers_for_device[prev_name] = prev_data["github"]

                current_maintainers_for_device = {}
                for curr_name, curr_data in current_maintainers_data.items():
                    if codename in curr_data.get("currently_maintains", set()):
                        current_maintainers_for_device[curr_name] = curr_data["github"]

                for old_maintainer_name, old_maintainer_github in previous_maintainers_for_device.items():
                    if old_maintainer_name not in current_maintainers_for_device:
                        if old_maintainer_name in current_maintainers_data:
                            current_maintainers_data[old_maintainer_name]["used_to_maintain"].add(codename)
                            if codename in current_maintainers_data[old_maintainer_name]["currently_maintains"]:
                                current_maintainers_data[old_maintainer_name]["currently_maintains"].remove(codename)
                        elif old_maintainer_name not in current_maintainers_data and old_maintainer_name in previous_maintainers_data:
                            if old_maintainer_name not in current_maintainers_data:
                                current_maintainers_data[old_maintainer_name] = {
                                    "github": previous_maintainers_data[old_maintainer_name]["github"],
                                    "currently_maintains": set(),
                                    "used_to_maintain": previous_maintainers_data[old_maintainer_name]["used_to_maintain"] | {codename},
                                }
                            elif codename not in current_maintainers_data[old_maintainer_name]["used_to_maintain"]:
                                current_maintainers_data[old_maintainer_name]["used_to_maintain"].add(codename)

    active_maintainers_list = []
    inactive_maintainers_list = []

    for name, data in current_maintainers_data.items():
        maintainer_info = {
            "name": name,
            "github": data["github"],
        }
        if data["currently_maintains"]:
            maintainer_info["currently_maintains"] = sorted(list(data["currently_maintains"]))
            if data["used_to_maintain"]:
                maintainer_info["used_to_maintain"] = sorted(list(data["used_to_maintain"]))
            active_maintainers_list.append(maintainer_info)
        elif data["used_to_maintain"]:
            maintainer_info["used_to_maintain"] = sorted(list(data["used_to_maintain"]))
            inactive_maintainers_list.append(maintainer_info)

    active_maintainers_list.sort(key=lambda x: x["name"])
    inactive_maintainers_list.sort(key=lambda x: x["name"])

    output_data = {
        "active_maintainers": active_maintainers_list,
        "inactive_maintainers": inactive_maintainers_list,
    }

    with open("maintainers.json", "w") as f:
        json.dump(output_data, f, indent=2)
        f.write("\n")

    print(f"\n✅ Wrote {len(active_maintainers_list)} active maintainers to maintainers.json")
    print(f"✅ Wrote {len(inactive_maintainers_list)} inactive maintainers to maintainers.json")

if __name__ == "__main__":
    main()
