#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import re
from datetime import datetime

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = text.strip('-')
    return text

def load_blog_ids():
    blog_ids_path = "blogs.json"
    if os.path.exists(blog_ids_path):
        try:
            with open(blog_ids_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: blogs.json is empty or malformed. Starting with an empty list.")
            return []
    else:
        return []

def save_blog_ids(blog_ids):
    with open("blogs.json", "w") as f:
        json.dump(blog_ids, f, indent=2)
        f.write("\n")

def prompt_blog_details(existing_blog_ids):
    print("Creating a new blog entry...\n")

    github = input("Enter the author's GitHub username (e.g., Evolution-X): ").strip()
    if not github:
        github = "Unknown"

    author = input("Enter the author's name (e.g., The Evolution-X Team): ").strip()
    while re.search(r'\d', author):
        print("Error: Author name should not contain numbers. Please try again.")
        author = input("Enter the author's name: ").strip()
    if not author:
        author = "Anonymous"

    while True:
        title_input = input("Enter the title of the blog (this will also be its ID): ").strip()
        if not title_input:
            print("Error: Blog title cannot be empty. Please try again.")
            continue

        blog_id = slugify(title_input)
        if blog_id in existing_blog_ids:
            print(f"Error: A blog with the ID '{blog_id}' (from title '{title_input}') already exists. Please choose a different title.")
        else:
            break

    print(f"Blog ID (filename) will be: {blog_id}")

    current_date = datetime.now().strftime("%m-%d-%Y")
    print(f"Date will be set to: {current_date}")

    print("Enter the content of the blog (press Enter twice to finish):")
    content_lines = []
    while True:
        line = input()
        if not line:
            break
        content_lines.append(line)
    content = "\n".join(content_lines)

    blog_data = {
        "github": github,
        "author": author,
        "title": title_input,
        "content": content,
        "date": current_date
    }

    return blog_data, blog_id

def save_blog(blog_data, blog_id):
    posts_dir = "posts"
    os.makedirs(posts_dir, exist_ok=True)
    blog_filename = os.path.join(posts_dir, f"{blog_id}.json")
    with open(blog_filename, "w", encoding="utf-8") as f:
        json.dump(blog_data, f, indent=2, ensure_ascii=False)
        f.write("\n")

def main():
    blog_ids = load_blog_ids()

    new_blog_data, blog_id_to_save = prompt_blog_details(blog_ids)

    if new_blog_data and blog_id_to_save:
        save_blog(new_blog_data, blog_id_to_save)

        blog_ids.append(blog_id_to_save)
        save_blog_ids(blog_ids)

        print("\nBlog created and saved successfully!")
        print(f"Blog ID (filename): {blog_id_to_save}")
        print(f"Github: {new_blog_data['github']}")
        print(f"Author: {new_blog_data['author']}")
        print(f"Title: {new_blog_data['title']}")
        print(f"Content: {new_blog_data['content']}")
        print(f"Date: {new_blog_data['date']}")

if __name__ == "__main__":
    main()
