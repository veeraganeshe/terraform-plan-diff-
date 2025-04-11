import re
import os
import csv
import argparse
from datetime import datetime

def parse_plan_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    plan_summary = next((line.strip() for line in lines if line.strip().startswith("Plan:")), "Plan summary not found.")

    resource_header_pattern = re.compile(
        r'#\s+(\S+)\.(\S+)(?:\["(.+?)"\])?\s+will\s+(be\s+)?(created|updated\s+in-place|destroyed)', re.IGNORECASE
    )
    attribute_change_pattern = re.compile(
        r'~\s+(\w+)\s+=\s+"?(.*?)"?\s+->\s+"?(.*?)"?\s*$'
    )

    summary = []
    current_resource = None

    for line in lines:
        line = line.strip()

        res_match = resource_header_pattern.match(line)
        if res_match:
            res_type = res_match.group(1)
            res_name = res_match.group(2)
            index = res_match.group(3)
            action = res_match.group(5).lower()

            full_name = f'{res_name}["{index}"]' if index else res_name
            current_resource = {
                "type": res_type,
                "name": full_name,
                "action": "Add" if "create" in action else "Update" if "update" in action else "Destroy",
                "changes": []
            }
            summary.append(current_resource)

        elif current_resource and attribute_change_pattern.match(line):
            attr_match = attribute_change_pattern.match(line)
            key, old, new = attr_match.group(1), attr_match.group(2), attr_match.group(3)
            current_resource["changes"].append(f'{key}: {old} -> {new}')

    return plan_summary, summary

def print_summary_to_console(plan_summary, summary, env):
    print(f"\n[PLAN] Terraform Plan Summary – {env}")
    print(plan_summary)
    print("\n| Environment        | Action   | Resource Type              | Resource Name                          |")
    print("|--------------------|----------|----------------------------|----------------------------------------|")

    for res in summary:
        print(f"| {env:<18} | {res['action']:<8} | {res['type']:<26} | {res['name']:<38} |")
        if res["changes"]:
            for change in res["changes"]:
                print(f"{'':<90}  -> {change}")
        else:
            print(f"{'':<90}  -> No attribute changes")

def write_summary_to_csv(summary, env, plan_summary, filename=None):
    timestamp = datetime.now()
    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    filename = filename or f"plan_summary_{env}_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.csv"

    with open(filename, mode="w", newline='', encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Generated At:", timestamp_str])
        writer.writerow([plan_summary])
        writer.writerow([])  # blank line
        writer.writerow(["Environment", "Action", "Resource Type", "Resource Name", "Change"])

        for res in summary:
            if res["changes"]:
                for change in res["changes"]:
                    writer.writerow([env, res["action"], res["type"], res["name"], change])
            else:
                writer.writerow([env, res["action"], res["type"], res["name"], "No attribute changes"])

    print(f"\n[OK] Exported to {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse Terraform/Terragrunt plan output.")
    parser.add_argument("file", help="Path to plan output file (e.g., plan-files/dbx-outputplan.txt)")
    parser.add_argument("--env", default="default", help="Environment label (e.g., cloudwatch, lambda, dbx)")

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"❌ Error: File '{args.file}' not found.")
    else:
        plan_summary, parsed_summary = parse_plan_file(args.file)
        print_summary_to_console(plan_summary, parsed_summary, env=args.env)
        write_summary_to_csv(parsed_summary, env=args.env, plan_summary=plan_summary)
