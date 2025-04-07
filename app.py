from flask import Flask, render_template, request, jsonify
import asyncio
import aiohttp
import base64

app = Flask(__name__)

async def post_to_wordpress(session, domain, username, password, post_data):
    auth = base64.b64encode(f'{username}:{password}'.encode()).decode()
    headers = {
        'Authorization': f'Basic {auth}',
        'Content-Type': 'application/json'
    }
    url = f'https://{domain}/wp-json/wp/v2/posts'
    
    try:
        async with session.post(url, headers=headers, json=post_data) as response:
            if response.status == 201:
                return f'Successfully posted to {domain}'
            else:
                response_text = await response.text()
                return f'Failed to post to {domain}: HTTP {response.status} - {response_text}'
    except Exception as e:
        return f'Error posting to {domain}: {str(e)}'

async def get_category_ids(session, domain, username, password, categories):
    ids = []
    for category in categories:
        url = f"https://{domain}/wp-json/wp/v2/categories?search={category}"
        auth = base64.b64encode(f'{username}:{password}'.encode()).decode()
        headers = {'Authorization': f'Basic {auth}'}
        
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data:
                        ids.append(data[0]['id'])
                    else:
                        created_id = await create_category(session, domain, username, password, category)
                        ids.append(created_id)
        except Exception as e:
            print(f"Error fetching category '{category}' on {domain}: {str(e)}")
    return ids

async def get_tag_ids(session, domain, username, password, tags):
    ids = []
    for tag in tags:
        url = f"https://{domain}/wp-json/wp/v2/tags?search={tag}"
        auth = base64.b64encode(f'{username}:{password}'.encode()).decode()
        headers = {'Authorization': f'Basic {auth}'}
        
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data:
                        ids.append(data[0]['id'])
                    else:
                        created_id = await create_tag(session, domain, username, password, tag)
                        ids.append(created_id)
        except Exception as e:
            print(f"Error fetching tag '{tag}' on {domain}: {str(e)}")
    return ids

async def post_to_multiple_domains(domains, post_title, post_content, categories, tags):
    post_data = {
        'title': post_title,
        'content': post_content,
        'status': 'draft',
    }
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for domain, username, password in domains:
            cat_ids = await get_category_ids(session, domain, username, password, categories)
            tag_ids = await get_tag_ids(session, domain, username, password, tags)
            post_data['categories'] = cat_ids
            post_data['tags'] = tag_ids
            task = post_to_wordpress(session, domain, username, password, post_data)
            tasks.append(task)
        
        return await asyncio.gather(*tasks)

@app.route('/submit_post', methods=['POST'])
def submit_post():
    post_title = request.form['postTitle']
    post_content = request.form['postContent']
    domain_input = request.form['domain']
    categories = request.form['categories'].split(',')
    tags = request.form['tags'].split(',')
    
    domains = [tuple(domain.strip().split(':')) for domain in domain_input.splitlines()]
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    tasks = loop.run_until_complete(post_to_multiple_domains(domains, post_title, post_content, categories, tags))
    
    # Mengembalikan log sebagai response JSON
    return jsonify({'log': '\n'.join(tasks)})

if __name__ == '__main__':
    app.run(debug=True)
