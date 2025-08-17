def test_search_empty_query(client):
    r = client.get('/api/v1/search/', query_string={'q': ''})
    assert r.status_code == 200
    data = r.get_json()['data']
    assert data['total'] == 0


def test_search_pagination_has_next(client, monkeypatch):
    # Mock index with predictable total and hits
    class DummyIdx2:
        def search(self, q, params=None):
            # simulate 25 total hits, return a slice based on offset/limit
            limit = params.get('limit', 10)
            offset = params.get('offset', 0)
            all_hits = []
            for i in range(25):
                all_hits.append({'id': i+1, 'title': f'Title {i+1}', 'content': f'Content {i+1}', 'tags': ['t1','t2'], 'status':'published','category_id':1,'author_id':1,'published_at':'2024-01-01T00:00:00Z','_formatted': {}})
            hits = all_hits[offset:offset+limit]
            return {'estimatedTotalHits': 25, 'hits': hits}
    monkeypatch.setattr('app.search.client.ensure_index', lambda: DummyIdx2(), raising=False)
    monkeypatch.setattr('app.search.indexer.ensure_index', lambda: DummyIdx2(), raising=False)

    r = client.get('/api/v1/search/', query_string={'q': 'Title','page_size':10,'page':2})
    assert r.status_code == 200
    data = r.get_json()['data']
    assert data['page'] == 2
    assert data['has_next'] is True  # 2*10 < 25

    r2 = client.get('/api/v1/search/', query_string={'q': 'Title','page_size':10,'page':3})
    assert r2.status_code == 200
    data2 = r2.get_json()['data']
    assert data2['has_next'] is False  # 3*10 >= 25


def test_search_multitag_and_or(client, monkeypatch):
    # Provide two documents with different tag combinations
    class DummyIdx3:
        def search(self, q, params=None):
            # Inspect filter clauses to simulate AND/OR behaviors
            filters = params.get('filter', []) if params else []
            # Build a simplified result set based on presence of both tags conditions
            docs = [
                {'id':1,'title':'A','content':'A','tags':['go','python'],'status':'published','category_id':1,'author_id':1,'published_at':'2024-01-01T00:00:00Z','_formatted': {}},
                {'id':2,'title':'B','content':'B','tags':['go'],'status':'published','category_id':1,'author_id':1,'published_at':'2024-01-01T00:00:00Z','_formatted': {}},
            ]
            # crude simulation: if filters contain two separate tag clauses treat as AND => only doc 1
            tag_clause_count = sum(1 for f in filters if isinstance(f, str) and f.startswith("tags = '"))
            if tag_clause_count >= 2:
                hits = [docs[0]]
            else:
                hits = docs
            return {'estimatedTotalHits': len(hits), 'hits': hits}
    monkeypatch.setattr('app.search.client.ensure_index', lambda: DummyIdx3(), raising=False)
    monkeypatch.setattr('app.search.indexer.ensure_index', lambda: DummyIdx3(), raising=False)

    # OR mode
    r_or = client.get('/api/v1/search/', query_string={'q':'x','tags':'go,python','match_mode':'or'})
    assert r_or.status_code == 200
    total_or = r_or.get_json()['data']['total']
    assert total_or == 2

    # AND mode
    r_and = client.get('/api/v1/search/', query_string={'q':'x','tags':'go,python','match_mode':'and'})
    assert r_and.status_code == 200
    total_and = r_and.get_json()['data']['total']
    assert total_and == 1


def test_version_diff_flow(client):
    # register & login
    client.post('/api/v1/auth/register', json={'email':'vd@test.com','password':'pass123'})
    login = client.post('/api/v1/auth/login', json={'email':'vd@test.com','password':'pass123'})
    token = login.get_json()['data']['access_token']

    # create article
    create = client.post('/api/v1/articles/', json={'title':'Diff文章','content_md':'第一版内容'}, headers={'Authorization':'Bearer '+token})
    art_id = create.get_json()['data']['id']

    # snapshot v1
    v1 = client.post(f'/api/v1/articles/{art_id}/versions', headers={'Authorization':'Bearer '+token})
    assert v1.status_code == 201

    # update article & snapshot v2
    client.put(f'/api/v1/articles/{art_id}', json={'content_md':'第二版内容\n新增一行'}, headers={'Authorization':'Bearer '+token})
    v2 = client.post(f'/api/v1/articles/{art_id}/versions', headers={'Authorization':'Bearer '+token})
    assert v2.status_code == 201

    # diff between v1 and v2
    diff = client.get(f'/api/v1/articles/{art_id}/versions/1/diff', query_string={'target':2}, headers={'Authorization':'Bearer '+token})
    assert diff.status_code == 200
    diff_lines = diff.get_json()['data']['diff']
    assert any(line.startswith('@@') for line in diff_lines)

    # invalid target
    diff_invalid = client.get(f'/api/v1/articles/{art_id}/versions/1/diff', query_string={'target':99}, headers={'Authorization':'Bearer '+token})
    assert diff_invalid.status_code == 404
