import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Fungsi untuk membuat postingan di beberapa domain
def create_posts_for_domains(domains, post_title, post_content, categories, tags):
    domain_results = {}

    for domain_data in domains:
        parts = domain_data.split(":")
        if len(parts) != 3:
            domain_results[domain_data] = "Format tidak valid"
            continue

        domain, username, password = parts
        cat_ids = get_category_ids(domain, username, password, categories)
        tag_ids = get_tag_ids(domain, username, password, tags)

        post_data = {
            'title': post_title,
            'content': post_content.replace('@Domain', domain).replace('@Judul', post_title),
            'status': 'draft',
            'categories': cat_ids,
            'tags': tag_ids
        }

        response = requests.post(
            f'https://{domain}/wp-json/wp/v2/posts',
            auth=(username, password),
            json=post_data
        )

        if response.status_code == 201:
            domain_results[domain] = True
        else:
            domain_results[domain] = f"HTTP {response.status_code}"

    return domain_results

# Fungsi untuk mendapatkan ID kategori
def get_category_ids(domain, username, password, categories):
    ids = []
    for name in categories:
        response = requests.get(
            f'https://{domain}/wp-json/wp/v2/categories',
            params={'search': name},
            auth=(username, password)
        )

        if response.status_code == 200:
            data = response.json()
            if data and 'id' in data[0]:
                ids.append(data[0]['id'])
            else:
                created = create_category(domain, username, password, name)
                if created:
                    ids.append(created)
    return ids

# Fungsi untuk mendapatkan ID tag
def get_tag_ids(domain, username, password, tags):
    ids = []
    for name in tags:
        response = requests.get(
            f'https://{domain}/wp-json/wp/v2/tags',
            params={'search': name},
            auth=(username, password)
        )

        if response.status_code == 200:
            data = response.json()
            if data and 'id' in data[0]:
                ids.append(data[0]['id'])
            else:
                created = create_tag(domain, username, password, name)
                if created:
                    ids.append(created)
    return ids

# Fungsi untuk membuat kategori jika tidak ada
def create_category(domain, username, password, name):
    response = requests.post(
        f'https://{domain}/wp-json/wp/v2/categories',
        auth=(username, password),
        json={'name': name}
    )
    if response.status_code == 201:
        return response.json().get('id')
    return None

# Fungsi untuk membuat tag jika tidak ada
def create_tag(domain, username, password, name):
    response = requests.post(
        f'https://{domain}/wp-json/wp/v2/tags',
        auth=(username, password),
        json={'name': name}
    )
    if response.status_code == 201:
        return response.json().get('id')
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit_post():
    post_title = request.form['postTitle']
    post_content = request.form['postContent']
    domain_input = request.form['domain']
    categories = request.form['categories']
    tags = request.form['tags']

    if not post_title or not post_content:
        return jsonify({'message': 'Judul dan konten harus diisi.'})
    elif not domain_input:
        return jsonify({'message': 'Harap masukkan domain.'})
    else:
        domains = [d.strip() for d in domain_input.split('\n') if d.strip()]
        categories = [c.strip() for c in categories.split(',') if c.strip()]
        tags = [t.strip() for t in tags.split(',') if t.strip()]

        if not categories:
            return jsonify({'message': 'Kategori tidak boleh kosong.'})
        elif not tags:
            return jsonify({'message': 'Tag tidak boleh kosong.'})
        else:
            domain_results = create_posts_for_domains(domains, post_title, post_content, categories, tags)

            success_domains = [domain for domain, result in domain_results.items() if result is True]
            failed_domains = [f"{domain} ({result})" for domain, result in domain_results.items() if result is not True]

            response_message = ''
            if success_domains:
                response_message += '\n'.join([f"{domain} berhasil" for domain in success_domains]) + '\n'
            if failed_domains:
                response_message += '\n'.join([f"{domain} gagal" for domain in failed_domains]) + '\n'

            return jsonify({'message': response_message})

if __name__ == '__main__':
    app.run(debug=True)
