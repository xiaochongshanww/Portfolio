from flask import Blueprint, jsonify
import logging, traceback  # 添加日志

openapi_bp = Blueprint('openapi', __name__)

# ================= PATHS =================
PATHS = {
    '/api/v1/ping': {
        'get': {
            'summary': 'Ping',
            'responses': {
                '200': {
                    'description': 'pong',
                    'content': {
                        'application/json': {
                            'schema': {'$ref': '#/components/schemas/StandardSuccess'}
                        }
                    }
                }
            },
            'security': []  # public
        }
    },
    '/api/v1/health': {
        'get': {
            'summary': 'Health',
            'responses': {
                '200': {
                    'description': 'OK',
                    'content': {
                        'application/json': {
                            'schema': {'$ref': '#/components/schemas/HealthResponse'}
                        }
                    }
                }
            },
            'security': []
        }
    },
    # Meta
    '/api/v1/meta/version': {
        'get': {
            'summary': 'App version',
            'responses': {
                '200': {
                    'description': 'OK',
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'properties': {
                                    'code': {'type': 'integer'},
                                    'message': {'type': 'string'},
                                    'data': {
                                        'type': 'object',
                                        'properties': {
                                            'version': {'type': 'string'},
                                            'git_commit': {'type': 'string'},
                                            'build_time': {'type': 'string'}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            'security': []
        }
    },
    '/api/v1/meta/error-codes': {
        'get': {
            'summary': 'List error codes',
            'description': '错误码目录：用于前端统一映射展示。',
            'responses': {
                '200': {
                    'description': 'OK',
                    'content': {
                        'application/json': {
                            'schema': {'$ref': '#/components/schemas/ErrorCodeCatalogResponse'}
                        }
                    }
                }
            },
            'security': []
        }
    },
    # Auth
    '/api/v1/auth/register': {
        'post': {
            'summary': 'Register',
            'requestBody': {
                'required': True,
                'content': {
                    'application/json': {'schema': {'$ref': '#/components/schemas/RegisterRequest'}}
                }
            },
            'responses': {
                '201': {
                    'description': 'Created',
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/RegisterResponse'}}
                    }
                },
                '409': {'$ref': '#/components/responses/Conflict'},
                '400': {'$ref': '#/components/responses/ValidationError'}
            }
        }
    },
    '/api/v1/auth/login': {
        'post': {
            'summary': 'Login',
            'requestBody': {
                'required': True,
                'content': {
                    'application/json': {'schema': {'$ref': '#/components/schemas/LoginRequest'}}
                }
            },
            'responses': {
                '200': {
                    'description': 'OK',
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/LoginResponse'}}
                    }
                },
                '401': {'$ref': '#/components/responses/Unauthorized'},
                '400': {'$ref': '#/components/responses/ValidationError'}
            }
        }
    },
    '/api/v1/auth/refresh': {
        'post': {
            'summary': 'Refresh access token',
            'responses': {
                '200': {
                    'description': 'OK',
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/RefreshResponse'}}
                    }
                },
                '401': {'$ref': '#/components/responses/Unauthorized'}
            }
        }
    },
    '/api/v1/auth/logout': {
        'post': {
            'summary': 'Logout',
            'responses': {
                '200': {
                    'description': 'OK',
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/StandardSuccess'}}
                    }
                }
            }
        }
    },
    '/api/v1/auth/change_password': {
        'post': {
            'summary': 'Change password',
            'requestBody': {
                'required': True,
                'content': {
                    'application/json': {'schema': {'$ref': '#/components/schemas/ChangePasswordRequest'}}
                }
            },
            'responses': {
                '200': {
                    'description': 'OK',
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/StandardSuccess'}}
                    }
                },
                '401': {'$ref': '#/components/responses/Unauthorized'},
                '400': {'$ref': '#/components/responses/ValidationError'}
            }
        }
    },
    # Users
    '/api/v1/users/me': {
        'get': {
            'summary': 'Get my profile',
            'responses': {
                '200': {
                    'description': 'OK',
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/UserDetailResponse'}}
                    }
                },
                '401': {'$ref': '#/components/responses/Unauthorized'}
            }
        },
        'patch': {
            'summary': 'Update my profile',
            'requestBody': {
                'required': True,
                'content': {
                    'application/json': {'schema': {'$ref': '#/components/schemas/ProfileUpdate'}}
                }
            },
            'responses': {
                '200': {
                    'description': 'Updated',
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/UserDetailResponse'}}
                    }
                },
                '400': {'$ref': '#/components/responses/ValidationError'},
                '401': {'$ref': '#/components/responses/Unauthorized'}
            }
        }
    },
    '/api/v1/users/': {
        'get': {
            'summary': 'List users (admin)',
            'description': '支持 ETag / If-None-Match',
            'parameters': [
                {'name': 'page', 'in': 'query', 'schema': {'type': 'integer'}},
                {'name': 'page_size', 'in': 'query', 'schema': {'type': 'integer'}}
            ],
            'responses': {
                '200': {
                    'description': 'OK',
                    'headers': {'ETag': {'schema': {'type': 'string'}}},
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/UserListResponse'}}
                    }
                },
                '304': {'description': 'Not Modified'},
                '403': {'$ref': '#/components/responses/Forbidden'}
            }
        }
    },
    '/api/v1/users/{user_id}/role': {
        'patch': {
            'summary': 'Change user role',
            'parameters': [
                {'name': 'user_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}
            ],
            'requestBody': {
                'required': True,
                'content': {
                    'application/json': {'schema': {'$ref': '#/components/schemas/RoleUpdate'}}
                }
            },
            'responses': {
                '200': {
                    'description': 'OK',
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/ChangeRoleResponse'}}
                    }
                },
                '400': {'$ref': '#/components/responses/ValidationError'},
                '403': {'$ref': '#/components/responses/Forbidden'}
            }
        }
    },
    '/api/v1/users/public/{user_id}': {
        'get': {
            'summary': 'Public author profile',
            'description': '支持 ETag / If-None-Match',
            'parameters': [
                {'name': 'user_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}
            ],
            'responses': {
                '200': {
                    'description': 'OK',
                    'headers': {'ETag': {'schema': {'type': 'string'}}},
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/UserPublicResponse'}}
                    }
                },
                '404': {'$ref': '#/components/responses/NotFound'},
                '304': {'description': 'Not Modified'}
            },
            'security': []
        }
    },
    '/api/v1/users/public/{user_id}/articles': {
        'get': {
            'summary': 'Public author published articles',
            'description': '支持 ETag / If-None-Match',
            'parameters': [
                {'name': 'user_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}},
                {'name': 'page', 'in': 'query', 'schema': {'type': 'integer'}},
                {'name': 'page_size', 'in': 'query', 'schema': {'type': 'integer'}},
                {'name': 'sort', 'in': 'query', 'schema': {'type': 'string'}}
            ],
            'responses': {
                '200': {
                    'description': 'OK',
                    'headers': {'ETag': {'schema': {'type': 'string'}}},
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/ArticleListResponse'}}
                    }
                },
                '404': {'$ref': '#/components/responses/NotFound'},
                '304': {'description': 'Not Modified'}
            },
            'security': []
        }
    },
    # Articles CRUD & workflow
    '/api/v1/articles/': {
        'post': {
            'summary': 'Create article',
            'requestBody': {
                'required': True,
                'content': {
                    'application/json': {'schema': {'$ref': '#/components/schemas/ArticleCreate'}}
                }
            },
            'responses': {
                '201': {
                    'description': 'Created',
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/ArticleDetailResponse'}}
                    }
                },
                '400': {'$ref': '#/components/responses/ValidationError'},
                '401': {'$ref': '#/components/responses/Unauthorized'},
                '403': {'$ref': '#/components/responses/Forbidden'},
                '409': {'$ref': '#/components/responses/Conflict'},
                '429': {'$ref': '#/components/responses/TooManyRequests'},
                '500': {'$ref': '#/components/responses/InternalServerError'}
            }
        },
        'get': {
            'summary': 'List articles',
            'description': '支持 ETag / If-None-Match',
            'parameters': [
                {'name': 'page', 'in': 'query', 'schema': {'type': 'integer'}},
                {'name': 'page_size', 'in': 'query', 'schema': {'type': 'integer'}},
                {'name': 'status', 'in': 'query', 'schema': {'type': 'string'}},
                {'name': 'tag', 'in': 'query', 'schema': {'type': 'string'}},
                {'name': 'category', 'in': 'query', 'schema': {'type': 'string'}}
            ],
            'responses': {
                '200': {
                    'description': 'OK',
                    'headers': {'ETag': {'schema': {'type': 'string'}}},
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/ArticleListResponse'}}
                    }
                },
                '304': {'description': 'Not Modified'},
                '401': {'$ref': '#/components/responses/Unauthorized'},
                '429': {'$ref': '#/components/responses/TooManyRequests'},
                '500': {'$ref': '#/components/responses/InternalServerError'}
            }
        }
    },
    '/api/v1/articles/{id}': {
        'get': {
            'summary': 'Get article detail',
            'description': '支持 ETag / If-None-Match',
            'parameters': [
                {'name': 'id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}
            ],
            'responses': {
                '200': {
                    'description': 'OK',
                    'headers': {'ETag': {'schema': {'type': 'string'}}},
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/ArticleDetailResponse'}}
                    }
                },
                '304': {'description': 'Not Modified'},
                '404': {'$ref': '#/components/responses/NotFound'},
                '401': {'$ref': '#/components/responses/Unauthorized'},
                '500': {'$ref': '#/components/responses/InternalServerError'}
            }
        },
        'put': {
            'summary': 'Update article',
            'parameters': [
                {'name': 'id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}
            ],
            'requestBody': {
                'required': True,
                'content': {
                    'application/json': {'schema': {'$ref': '#/components/schemas/ArticleUpdate'}}
                }
            },
            'responses': {
                '200': {
                    'description': 'OK',
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/ArticleDetailResponse'}}
                    }
                },
                '400': {'$ref': '#/components/responses/ValidationError'},
                '401': {'$ref': '#/components/responses/Unauthorized'},
                '403': {'$ref': '#/components/responses/Forbidden'},
                '404': {'$ref': '#/components/responses/NotFound'},
                '409': {'$ref': '#/components/responses/Conflict'},
                '429': {'$ref': '#/components/responses/TooManyRequests'},
                '500': {'$ref': '#/components/responses/InternalServerError'}
            }
        },
        'delete': {
            'summary': 'Delete article',
            'parameters': [
                {'name': 'id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}
            ],
            'responses': {
                '200': {
                    'description': 'OK',
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/DeleteArticleResponse'}}
                    }
                },
                '401': {'$ref': '#/components/responses/Unauthorized'},
                '403': {'$ref': '#/components/responses/Forbidden'},
                '404': {'$ref': '#/components/responses/NotFound'},
                '429': {'$ref': '#/components/responses/TooManyRequests'},
                '500': {'$ref': '#/components/responses/InternalServerError'}
            }
        }
    },
    '/api/v1/articles/slug/{slug}': {
        'get': {
            'summary': 'Get article by slug (internal)',
            'description': '支持 ETag / If-None-Match',
            'parameters': [
                {'name': 'slug', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}
            ],
            'responses': {
                '200': {
                    'description': 'OK',
                    'headers': {'ETag': {'schema': {'type': 'string'}}},
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/ArticleDetailResponse'}}
                    }
                },
                '404': {'$ref': '#/components/responses/NotFound'},
                '304': {'description': 'Not Modified'}
            }
        }
    },
    '/api/v1/articles/{id}/submit': {
        'post': {
            'summary': 'Submit article',
            'parameters': [
                {'name': 'id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}
            ],
            'responses': {
                '200': {
                    'description': 'OK',
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/WorkflowStatusResponse'}}
                    }
                },
                '400': {'$ref': '#/components/responses/ValidationError'},
                '403': {'$ref': '#/components/responses/Forbidden'}
            }
        }
    },
    '/api/v1/articles/{id}/approve': {
        'post': {
            'summary': 'Approve article',
            'parameters': [
                {'name': 'id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}
            ],
            'responses': {
                '200': {
                    'description': 'OK',
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/WorkflowStatusResponse'}}
                    }
                },
                '403': {'$ref': '#/components/responses/Forbidden'}
            }
        }
    },
    '/api/v1/articles/{id}/reject': {
        'post': {
            'summary': 'Reject article',
            'parameters': [
                {'name': 'id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}
            ],
            'requestBody': {
                'required': True,
                'content': {
                    'application/json': {'schema': {'$ref': '#/components/schemas/RejectRequest'}}
                }
            },
            'responses': {
                '200': {
                    'description': 'OK',
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/WorkflowStatusResponse'}}
                    }
                },
                '400': {'$ref': '#/components/responses/ValidationError'},
                '403': {'$ref': '#/components/responses/Forbidden'}
            }
        }
    },
    '/api/v1/articles/{id}/schedule': {
        'post': {
            'summary': 'Schedule article',
            'parameters': [
                {'name': 'id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}
            ],
            'requestBody': {
                'required': True,
                'content': {
                    'application/json': {'schema': {'type': 'object', 'properties': {'scheduled_at': {'type': 'string', 'format': 'date-time'}}, 'required': ['scheduled_at']}}
                }
            },
            'responses': {
                '200': {'description': 'OK'},
                '400': {'$ref': '#/components/responses/ValidationError'},
                '403': {'$ref': '#/components/responses/Forbidden'}
            }
        }
    },
    '/api/v1/articles/{id}/unschedule': {
        'post': {
            'summary': 'Unschedule',
            'parameters': [
                {'name': 'id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}
            ],
            'responses': {
                '200': {'description': 'OK'},
                '400': {'$ref': '#/components/responses/ValidationError'},
                '403': {'$ref': '#/components/responses/Forbidden'}
            }
        }
    },
    '/api/v1/articles/{id}/unpublish': {
        'post': {
            'summary': 'Unpublish',
            'parameters': [
                {'name': 'id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}
            ],
            'responses': {
                '200': {'description': 'OK'},
                '400': {'$ref': '#/components/responses/ValidationError'},
                '403': {'$ref': '#/components/responses/Forbidden'}
            }
        }
    },
    '/api/v1/articles/{id}/like': {
        'post': {
            'summary': 'Toggle like',
            'parameters': [
                {'name': 'id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}
            ],
            'responses': {
                '200': {
                    'description': 'OK',
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/LikeToggleResponse'}}
                    }
                },
                '401': {'$ref': '#/components/responses/Unauthorized'},
                '404': {'$ref': '#/components/responses/NotFound'},
                '429': {'$ref': '#/components/responses/TooManyRequests'}
            }
        }
    },
    '/api/v1/articles/{id}/bookmark': {
        'post': {
            'summary': 'Toggle bookmark',
            'parameters': [
                {'name': 'id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}
            ],
            'responses': {
                '200': {
                    'description': 'OK',
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/BookmarkToggleResponse'}}
                    }
                },
                '401': {'$ref': '#/components/responses/Unauthorized'},
                '404': {'$ref': '#/components/responses/NotFound'},
                '429': {'$ref': '#/components/responses/TooManyRequests'}
            }
        }
    },
    '/api/v1/articles/public/': {
        'get': {
            'summary': 'Public list published articles',
            'description': '支持 ETag / If-None-Match',
            'parameters': [
                {'name': 'page', 'in': 'query', 'schema': {'type': 'integer', 'minimum': 1}},
                {'name': 'page_size', 'in': 'query', 'schema': {'type': 'integer', 'minimum': 1, 'maximum': 50}},
                {'name': 'tag', 'in': 'query', 'schema': {'type': 'string'}},
                {'name': 'category_id', 'in': 'query', 'schema': {'type': 'integer'}},
                {'name': 'author_id', 'in': 'query', 'schema': {'type': 'integer'}},
                {'name': 'sort', 'in': 'query', 'schema': {'type': 'string', 'description': 'published_at:desc|published_at:asc|created_at:desc|created_at:asc|likes_count:desc|likes_count:asc|views_count:desc|views_count:asc'}}
            ],
            'responses': {
                '200': {
                    'description': 'OK',
                    'headers': {'ETag': {'schema': {'type': 'string'}}},
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/ArticleListResponse'}}
                    }
                },
                '304': {'description': 'Not Modified'},
                '429': {'$ref': '#/components/responses/TooManyRequests'},
                '500': {'$ref': '#/components/responses/InternalServerError'}
            },
            'security': []
        }
    },
    '/api/v1/articles/public/slug/{slug}': {
        'get': {
            'summary': 'Public get article by slug',
            'description': '支持 ETag / If-None-Match；views_count 为近实时去重浏览次数(同用户或 IP+UA 1 小时内只计 1 次)',
            'parameters': [
                {'name': 'slug', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}
            ],
            'responses': {
                '200': {
                    'description': 'OK',
                    'headers': {'ETag': {'schema': {'type': 'string'}}},
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/ArticleDetailResponse'}}
                    }
                },
                '404': {'$ref': '#/components/responses/NotFound'},
                '304': {'description': 'Not Modified'},
                '429': {'$ref': '#/components/responses/TooManyRequests'},
                '500': {'$ref': '#/components/responses/InternalServerError'}
            },
            'security': []
        }
    },
    '/api/v1/articles/public/hot': {
        'get': {
            'summary': 'Public hot articles ranking',
            'description': '基于窗口(默认48h)的去重浏览+点赞+时间衰减组合得分。score = log10(views+1)*0.7 + likes*0.5 + 1/(1+hours/24)。支持 page,page_size,window_hours。支持 ETag / If-None-Match',
            'parameters': [
                {'name': 'page', 'in': 'query', 'schema': {'type': 'integer', 'minimum': 1}},
                {'name': 'page_size', 'in': 'query', 'schema': {'type': 'integer', 'minimum': 1, 'maximum': 50}},
                {'name': 'window_hours', 'in': 'query', 'schema': {'type': 'integer', 'minimum': 1, 'maximum': 168}, 'description': '统计窗口(小时)，默认48，最大168(7天)'}
            ],
            'responses': {
                '200': {
                    'description': 'OK',
                    'headers': {'ETag': {'schema': {'type': 'string'}}},
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/ArticleListResponse'}}
                    }
                },
                '304': {'description': 'Not Modified'}
            },
            'security': []
        }
    },
    # Search
    '/api/v1/search/': {
        'get': {
            'summary': 'Search articles',
            'description': '全文搜索文章；支持 ETag；ranking rules 纳入 likes_count, views_count, published_at',
            'parameters': [
                {'name': 'q', 'in': 'query', 'schema': {'type': 'string'}, 'description': '关键词'},
                {'name': 'page', 'in': 'query', 'schema': {'type': 'integer', 'minimum': 1}},
                {'name': 'page_size', 'in': 'query', 'schema': {'type': 'integer', 'minimum': 1, 'maximum': 50}},
                {'name': 'status', 'in': 'query', 'schema': {'type': 'string'}},
                {'name': 'tag', 'in': 'query', 'schema': {'type': 'string'}},
                {'name': 'tags', 'in': 'query', 'schema': {'type': 'string'}},
                {'name': 'match_mode', 'in': 'query', 'schema': {'type': 'string', 'enum': ['any', 'all', 'phrase']}},
                {'name': 'category_id', 'in': 'query', 'schema': {'type': 'integer'}},
                {'name': 'author_id', 'in': 'query', 'schema': {'type': 'integer'}},
                {'name': 'sort', 'in': 'query', 'schema': {'type': 'string', 'description': 'published_at:desc|published_at:asc|created_at:desc|created_at:asc|likes_count:desc|likes_count:asc|views_count:desc|views_count:asc|_score:desc'}}
            ],
            'responses': {
                '200': {
                    'description': 'OK',
                    'headers': {'ETag': {'schema': {'type': 'string'}}},
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/SearchResultResponse'}}
                    }
                },
                '304': {'description': 'Not Modified'},
                '400': {'$ref': '#/components/responses/ValidationError'},
                '429': {'$ref': '#/components/responses/TooManyRequests'},
                '500': {'$ref': '#/components/responses/InternalServerError'}
            },
            'security': []
        }
    },
    # Versions
    '/api/v1/articles/{id}/versions': {
        'get': {
            'summary': 'List article versions',
            'tags': ['versions'],
            'parameters': [
                    {'name': 'id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}},
                    {'name': 'detail', 'in': 'query', 'schema': {'type': 'string'}, 'description': '传 1 返回内容字段'}
            ],
            'responses': {
                '200': {
                    'description': 'OK',
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/ArticleVersionListResponse'}}
                    }
                },
                '401': {'$ref': '#/components/responses/Unauthorized'},
                '403': {'$ref': '#/components/responses/Forbidden'},
                '404': {'$ref': '#/components/responses/NotFound'}
            }
        },
        'post': {
            'summary': 'Create article version (snapshot current)',
            'tags': ['versions'],
            'parameters': [
                {'name': 'id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}
            ],
            'responses': {
                '201': {  # changed from 200 to 201
                    'description': 'Created',
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/CreateVersionResponse'}}
                    }
                },
                '401': {'$ref': '#/components/responses/Unauthorized'},
                '403': {'$ref': '#/components/responses/Forbidden'},
                '404': {'$ref': '#/components/responses/NotFound'}
            }
        }
    },
        '/api/v1/articles/{id}/versions/{version_no}': {
            'get': {
                'summary': 'Get article version detail',
                'tags': ['versions'],
                'parameters': [
                    {'name': 'id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}},
                    {'name': 'version_no', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}
                ],
                'responses': {
                    '200': {
                        'description': 'OK',
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'object',
                                    'properties': {
                                        'code': {'type': 'integer'},
                                        'message': {'type': 'string'},
                                        'data': {
                                            'type': 'object',
                                            'properties': {
                                                'id': {'type': 'integer'},
                                                'version_no': {'type': 'integer'},
                                                'created_at': {'type': 'string'},
                                                'content_md': {'type': 'string'},
                                                'content_html': {'type': 'string'}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    '401': {'$ref': '#/components/responses/Unauthorized'},
                    '403': {'$ref': '#/components/responses/Forbidden'},
                    '404': {'$ref': '#/components/responses/NotFound'}
                }
            }
        },
        '/api/v1/articles/{id}/versions/{version_no}/rollback': {
            'post': {
                'summary': 'Rollback to version',
                'tags': ['versions'],
                'parameters': [
                    {'name': 'id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}},
                    {'name': 'version_no', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}
                ],
                'responses': {
                    '200': {
                        'description': 'OK',
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'object',
                                    'properties': {
                                        'code': {'type': 'integer'},
                                        'message': {'type': 'string'},
                                        'data': {
                                            'type': 'object',
                                            'properties': {
                                                'rolled_back_to': {'type': 'integer'},
                                                'new_version_no': {'type': 'integer'}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    '401': {'$ref': '#/components/responses/Unauthorized'},
                    '403': {'$ref': '#/components/responses/Forbidden'},
                    '404': {'$ref': '#/components/responses/NotFound'}
                }
            }
        },
    # Audit
    '/api/v1/audit/logs': {
        'get': {
            'summary': 'List audit logs',
            'tags': ['audit'],
            'parameters': [
                {'name': 'page', 'in': 'query', 'schema': {'type': 'integer'}},
                {'name': 'page_size', 'in': 'query', 'schema': {'type': 'integer'}},
                {'name': 'article_id', 'in': 'query', 'schema': {'type': 'integer', 'nullable': True}},
                {'name': 'action', 'in': 'query', 'schema': {'type': 'string', 'nullable': True}}
            ],
            'responses': {
                '200': {
                    'description': 'OK',
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/AuditLogListResponse'}}
                    }
                },
                '401': {'$ref': '#/components/responses/Unauthorized'},
                '403': {'$ref': '#/components/responses/Forbidden'}
            }
        }
    },
    # Comments
    '/api/v1/comments/article/{article_id}/tree': {
        'get': {
            'summary': 'Get comment tree for article',
            'tags': ['comments'],
            'parameters': [
                {'name': 'article_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}
            ],
            'responses': {
                '200': {
                    'description': 'OK',
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/CommentTreeResponse'}}
                    }
                },
                '404': {'$ref': '#/components/responses/NotFound'}
            }
        }
    },
    '/api/v1/comments/pending': {
        'get': {
            'summary': 'List pending comments (moderation queue)',
            'tags': ['comments'],
            'parameters': [
                {'name': 'page', 'in': 'query', 'schema': {'type': 'integer'}},
                {'name': 'page_size', 'in': 'query', 'schema': {'type': 'integer'}}
            ],
            'responses': {
                '200': {
                    'description': 'OK',
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/CommentPendingListResponse'}}
                    }
                },
                '401': {'$ref': '#/components/responses/Unauthorized'},
                '403': {'$ref': '#/components/responses/Forbidden'}
            }
        }
    },
    # Uploads
    '/api/v1/uploads/image': {
        'post': {
            'summary': 'Upload image',
            'tags': ['uploads'],
            'requestBody': {
                'required': True,
                'content': {
                    'multipart/form-data': {
                        'schema': {
                            'type': 'object',
                            'properties': {
                                'file': {'type': 'string', 'format': 'binary'}
                            },
                            'required': ['file']
                        }
                    }
                }
            },
            'responses': {  # moved out of requestBody
                '200': {
                    'description': 'OK',
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/UploadImageResponse'}}
                    }
                },
                '400': {'$ref': '#/components/responses/ValidationError'},
                '401': {'$ref': '#/components/responses/Unauthorized'},
                '413': {'description': 'Payload Too Large', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/StandardError'}}}},
                '415': {'description': 'Unsupported Media Type', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/StandardError'}}}},
                '429': {'$ref': '#/components/responses/TooManyRequests'}
            }
        }
    },
    '/sitemap.xml': {
        'get': {
            'summary': 'Sitemap XML',
            'responses': {
                '200': {'description': 'OK'}
            },
            'security': []
        }
    },
    '/robots.txt': {
        'get': {
            'summary': 'Robots.txt',
            'responses': {
                '200': {'description': 'OK'}
            },
            'security': []
        }
    }
}

# ================= RESPONSES =================
RESPONSES = {
    'NotFound': {'description': 'Not Found', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/StandardError'}}}},
    'Unauthorized': {'description': 'Unauthorized', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/StandardError'}}}},
    'Forbidden': {'description': 'Forbidden', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/StandardError'}}}},
    'ValidationError': {'description': 'Validation Error', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ValidationError'}}}},
    'Conflict': {'description': 'Conflict', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/StandardError'}}}},
    'TooManyRequests': {'description': 'Too Many Requests', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/StandardError'}}}},
    'InternalServerError': {'description': 'Internal Server Error', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/StandardError'}}}}
}

# ================= SCHEMAS =================
SCHEMAS = {
    # Generic
    'StandardSuccess': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {}
        }
    },
    'StandardError': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'}
        }
    },
    'ValidationError': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {'type': 'array', 'items': {'type': 'object'}}
        }
    },
    'HealthResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {'type': 'object'}
        }
    },
    'PaginationMeta': {
        'type': 'object',
        'properties': {
            'total': {'type': 'integer'},
            'page': {'type': 'integer'},
            'page_size': {'type': 'integer'},
            'has_next': {'type': 'boolean'}
        }
    },
    # User
    'UserPublic': {
        'type': 'object',
        'properties': {
            'id': {'type': 'integer'},
            'nickname': {'type': 'string'},
            'bio': {'type': 'string'},
            'avatar': {'type': 'string'},
            'role': {'type': 'string'},
            'social_links': {'type': 'object', 'nullable': True},
            'published_articles': {'type': 'integer', 'nullable': True}
        }
    },
    'UserDetail': {
        'allOf': [
            {'$ref': '#/components/schemas/UserPublic'},
            {'type': 'object', 'properties': {'email': {'type': 'string'}}}
        ]
    },
    'UserDetailResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {'$ref': '#/components/schemas/UserDetail'}
        }
    },
    'UserPublicResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {'$ref': '#/components/schemas/UserPublic'}
        }
    },
    'UserListResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {
                'allOf': [
                    {'$ref': '#/components/schemas/PaginationMeta'},
                    {
                        'type': 'object',
                        'properties': {
                            'list': {
                                'type': 'array',
                                'items': {'$ref': '#/components/schemas/UserDetail'}
                            }
                        }
                    }
                ]
            }
        }
    },
    'ProfileUpdate': {
        'type': 'object',
        'properties': {
            'nickname': {'type': 'string'},
            'bio': {'type': 'string'},
            'avatar': {'type': 'string'},
            'social_links': {'type': 'object'}
        }
    },
    'RoleUpdate': {
        'type': 'object',
        'properties': {
            'role': {'type': 'string'}
        },
        'required': ['role']
    },
    'ChangeRoleResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'old_role': {'type': 'string'},
                    'new_role': {'type': 'string'}
                }
            }
        }
    },
    # Auth
    'RegisterRequest': {
        'type': 'object',
        'properties': {
            'email': {'type': 'string'},
            'password': {'type': 'string'}
        },
        'required': ['email', 'password']
    },
    'RegisterResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'email': {'type': 'string'}
                }
            }
        }
    },
    'LoginRequest': {
        'type': 'object',
        'properties': {
            'email': {'type': 'string'},
            'password': {'type': 'string'}
        },
        'required': ['email', 'password']
    },
    'LoginResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {
                'type': 'object',
                'properties': {
                    'access_token': {'type': 'string'},
                    'role': {'type': 'string'}
                }
            }
        }
    },
    'RefreshResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {
                'type': 'object',
                'properties': {
                    'access_token': {'type': 'string'}
                }
            }
        }
    },
    'ChangePasswordRequest': {
        'type': 'object',
        'properties': {
            'email': {'type': 'string'},
            'old_password': {'type': 'string'},
            'new_password': {'type': 'string'}
        },
        'required': ['email', 'old_password', 'new_password']
    },
    # Article
    'ArticleSummary': {
        'type': 'object',
        'properties': {
            'id': {'type': 'integer'},
            'title': {'type': 'string'},
            'slug': {'type': 'string'},
            'status': {'type': 'string'},
            'published_at': {'type': 'string', 'format': 'date-time', 'nullable': True},
            'created_at': {'type': 'string', 'format': 'date-time', 'nullable': True},
            'tags': {'type': 'array', 'items': {'type': 'string'}},
            'likes_count': {'type': 'integer'},
            'views_count': {'type': 'integer', 'description': '近实时去重浏览次数'},
            'score': {'type': 'number', 'nullable': True, 'description': '热门/搜索时的得分'}
        }
    },
    'ArticleDetail': {
        'allOf': [
            {'$ref': '#/components/schemas/ArticleSummary'},
            {
                'type': 'object',
                'properties': {
                    'content_html': {'type': 'string', 'description': '清洗后的安全 HTML'},
                    'content_md': {'type': 'string'},
                    'summary': {'type': 'string'},
                    'seo_title': {'type': 'string'},
                    'seo_desc': {'type': 'string'}
                }
            }
        ]
    },
    'ArticleDetailResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {'$ref': '#/components/schemas/ArticleDetail'}
        }
    },
    'ArticleListResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {
                'allOf': [
                    {'$ref': '#/components/schemas/PaginationMeta'},
                    {
                        'type': 'object',
                        'properties': {
                            'list': {
                                'type': 'array',
                                'items': {'$ref': '#/components/schemas/ArticleSummary'}
                            }
                        }
                    }
                ]
            }
        }
    },
    'ArticleCreate': {
        'type': 'object',
        'properties': {
            'title': {'type': 'string'},
            'slug': {'type': 'string'},
            'content_md': {'type': 'string'},
            'summary': {'type': 'string'},
            'seo_title': {'type': 'string'},
            'seo_desc': {'type': 'string'},
            'featured_image': {'type': 'string'},
            'category_id': {'type': 'integer'},
            'scheduled_at': {'type': 'string'},
            'tags': {'type': 'array', 'items': {'type': 'string'}}
        },
        'required': ['title']
    },
    'ArticleUpdate': {
        'type': 'object',
        'properties': {
            'title': {'type': 'string'},
            'slug': {'type': 'string'},
            'content_md': {'type': 'string'},
            'summary': {'type': 'string'},
            'seo_title': {'type': 'string'},
            'seo_desc': {'type': 'string'},
            'featured_image': {'type': 'string'},
            'category_id': {'type': 'integer'},
            'scheduled_at': {'type': 'string'},
            'tags': {'type': 'array', 'items': {'type': 'string'}}
        }
    },
    'DeleteArticleResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'deleted': {'type': 'boolean'}
                }
            }
        }
    },
    'WorkflowStatusResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {'type': 'object', 'properties': {'id': {'type': 'integer'}, 'status': {'type': 'string'}}}
        }
    },
    'LikeToggleResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {'type': 'object', 'properties': {'action': {'type': 'string'}, 'likes_count': {'type': 'integer'}}}
        }
    },
    # Versions
    'ArticleVersion': {
        'type': 'object',
        'properties': {
            'id': {'type': 'integer'},
            'version_no': {'type': 'integer'},
            'created_at': {'type': 'string', 'format': 'date-time'}
        }
    },
    'ArticleVersionListResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {'type': 'array', 'items': {'$ref': '#/components/schemas/ArticleVersion'}}
        }
    },
    'CreateVersionResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {'type': 'object', 'properties': {'version_no': {'type': 'integer'}}}
        }
    },
    'RollbackVersionResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {'type': 'object', 'properties': {'rolled_back_to': {'type': 'integer'}, 'new_version_no': {'type': 'integer'}}}
        }
    },
    'DiffVersionResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {
                'type': 'object',
                'properties': {
                    'from': {'type': 'integer'},
                    'to': {'type': 'integer'},
                    'diff': {'type': 'array', 'items': {'type': 'string'}}
                }
            }
        }
    },
    # Audit
    'AuditLogEntry': {
        'type': 'object',
        'properties': {
            'id': {'type': 'integer'},
            'action': {'type': 'string'},
            'note': {'type': 'string', 'nullable': True},
            'operator_id': {'type': 'integer'},
            'created_at': {'type': 'string', 'format': 'date-time'}
        }
    },
    'AuditLogListResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {
                'allOf': [
                    {'$ref': '#/components/schemas/PaginationMeta'},
                    {
                        'type': 'object',
                        'properties': {
                            'list': {
                                'type': 'array',
                                'items': {'$ref': '#/components/schemas/AuditLogEntry'}
                            }
                        }
                    }
                ]
            }
        }
    },
    # Taxonomy
    'Category': {
        'type': 'object',
        'properties': {
            'id': {'type': 'integer'},
            'name': {'type': 'string'},
            'slug': {'type': 'string'},
            'parent_id': {'type': 'integer', 'nullable': True}
        }
    },
    'CategoryDetailResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {'$ref': '#/components/schemas/Category'}
        }
    },
    'CategoryListResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {'type': 'array', 'items': {'$ref': '#/components/schemas/Category'}}
        }
    },
    'CategoryCreate': {
        'type': 'object',
        'properties': {
            'name': {'type': 'string'},
            'slug': {'type': 'string'},
            'parent_id': {'type': 'integer'}
        },
        'required': ['name']
    },
    'CategoryUpdate': {
        'type': 'object',
        'properties': {
            'name': {'type': 'string'},
            'slug': {'type': 'string'},
            'parent_id': {'type': 'integer'}
        }
    },
    'Tag': {
        'type': 'object',
        'properties': {
            'id': {'type': 'integer'},
            'name': {'type': 'string'},
            'slug': {'type': 'string'}
        }
    },
    'TagDetailResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {'$ref': '#/components/schemas/Tag'}
        }
    },
    'TagListResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {'type': 'array', 'items': {'$ref': '#/components/schemas/Tag'}}
        }
    },
    'TagCreate': {
        'type': 'object',
        'properties': {
            'name': {'type': 'string'},
            'slug': {'type': 'string'}
        },
        'required': ['name']
    },
    'TagUpdate': {
        'type': 'object',
        'properties': {
            'name': {'type': 'string'},
            'slug': {'type': 'string'}
        }
    },
    # Comments
    'Comment': {
        'type': 'object',
        'properties': {
            'id': {'type': 'integer'},
            'parent_id': {'type': 'integer', 'nullable': True},
            'content': {'type': 'string'},
            'created_at': {'type': 'string', 'format': 'date-time'},
            'user_id': {'type': 'integer'}
        }
    },
    'CommentCreate': {
        'type': 'object',
        'properties': {
            'article_id': {'type': 'integer'},
            'content': {'type': 'string'},
            'parent_id': {'type': 'integer'}
        },
        'required': ['article_id', 'content']
    },
    'CommentCreateResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'status': {'type': 'string'}
                }
            }
        }
    },
    'CommentModerate': {
        'type': 'object',
        'properties': {'action': {'type': 'string'}},
        'required': ['action']
    },
    'CommentListResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {'type': 'array', 'items': {'$ref': '#/components/schemas/Comment'}}
        }
    },
    'CommentTreeNode': {
        'type': 'object',
        'properties': {
            'id': {'type': 'integer'},
            'parent_id': {'type': 'integer', 'nullable': True},
            'content': {'type': 'string'},
            'created_at': {'type': 'string', 'format': 'date-time'},
            'user_id': {'type': 'integer'},
            'children': {'type': 'array', 'items': {'$ref': '#/components/schemas/CommentTreeNode'}}
        }
    },
    'CommentTreeResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {'type': 'array', 'items': {'$ref': '#/components/schemas/CommentTreeNode'}}
        }
    },
    'CommentPendingListResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {
                'allOf': [
                    {'$ref': '#/components/schemas/PaginationMeta'},
                    {
                        'type': 'object',
                        'properties': {
                            'list': {
                                'type': 'array',
                                'items': {'$ref': '#/components/schemas/Comment'}
                            }
                        }
                    }
                ]
            }
        }
    },
    # Search
    'SearchResultItem': {
        'allOf': [
            {'$ref': '#/components/schemas/ArticleSummary'},
            {
                'type': 'object',
                'properties': {
                    'highlight': {'type': 'object', 'nullable': True, 'description': '高亮片段'},
                    'score': {'type': 'number', 'nullable': True, 'description': '搜索相关性得分'}
                }
            }
        ]
    },
    'SearchResultResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {
                'allOf': [
                    {'$ref': '#/components/schemas/PaginationMeta'},
                    {
                        'type': 'object',
                        'properties': {
                            'query': {'type': 'string', 'nullable': True},
                            'filters': {
                                'type': 'object',
                                'properties': {
                                    'status': {'type': 'string', 'nullable': True},
                                    'tags': {'type': 'array', 'items': {'type': 'string'}},
                                    'category_id': {'type': 'integer', 'nullable': True},
                                    'author_id': {'type': 'integer', 'nullable': True},
                                    'match_mode': {'type': 'string', 'nullable': True},
                                    'sort': {'type': 'string', 'nullable': True}
                                }
                            },
                            'list': {'type': 'array', 'items': {'$ref': '#/components/schemas/SearchResultItem'}}
                        }
                    }
                ]
            }
        }
    },
    # Errors catalog
    'ErrorCodeItem': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'description': {'type': 'string'}
        }
    },
    'ErrorCodeCatalogResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {'type': 'array', 'items': {'$ref': '#/components/schemas/ErrorCodeItem'}}
        }
    },
    # Uploads
    'UploadImageResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {
                'type': 'object',
                'properties': {
                    'url': {'type': 'string'},
                    'width': {'type': 'integer', 'nullable': True},
                    'height': {'type': 'integer', 'nullable': True},
                    'size': {'type': 'integer'},
                    'variants': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'label': {'type': 'string'},
                                'url': {'type': 'string'},
                                'width': {'type': 'integer'},
                                'height': {'type': 'integer'},
                                'size': {'type': 'integer'}
                            }
                        }
                    },
                    'webp': {
                        'type': 'object',
                        'nullable': True,
                        'properties': {
                            'url': {'type': 'string'},
                            'width': {'type': 'integer'},
                            'height': {'type': 'integer'},
                            'size': {'type': 'integer'}
                        }
                    }
                }
            }
        }
    }
}
SCHEMAS.update({
    'BookmarkToggleResponse': {
        'type': 'object',
        'properties': {
            'code': {'type': 'integer'},
            'message': {'type': 'string'},
            'data': {
                'type': 'object',
                'properties': {
                    'action': {'type': 'string', 'description': 'bookmarked 或 removed'}
                }
            }
        }
    },
    'RejectRequest': {
        'type': 'object',
        'properties': {
            'reason': {'type': 'string', 'description': '拒绝原因'}
        },
        'required': ['reason']
    }
})
SCHEMAS.get('ErrorCodeCatalogResponse', {}).setdefault('example', {
    'code': 0,
    'message': 'ok',
    'data': [
        {'code': 0, 'message': 'ok', 'description': '成功'},
        {'code': 1001, 'message': '参数无效', 'description': '提交的数据校验失败'},
        {'code': 2003, 'message': '未授权', 'description': '缺少或无效的访问令牌'}
    ]
})

# ============== Auto tag inference ==============
AUTO_TAG_RULES = [
    ('/api/v1/auth/', 'auth'),
    ('/api/v1/users', 'users'),
    ('/api/v1/articles/{id}/versions', 'versions'),
    ('/api/v1/articles/{id}/', 'workflow'),
    ('/api/v1/articles/public', 'articles'),
    ('/api/v1/articles/bookmarks/', 'bookmarks'),
    ('/api/v1/articles/', 'articles'),
    ('/api/v1/search/', 'search'),
    ('/api/v1/comments/', 'comments'),
    ('/api/v1/audit/', 'audit'),
    ('/api/v1/uploads/', 'uploads'),
    ('/api/v1/meta/', 'meta'),
    ('/api/v1/categories/', 'taxonomy'),
    ('/api/v1/tags/', 'taxonomy'),
]

# 统一创建类接口状态码 -> 201 (补充 register/articles/version 创建)
CREATE_OPERATION_SIGNATURES = [
    ('/api/v1/auth/register', 'post'),
    ('/api/v1/articles/', 'post'),
    ('/api/v1/articles', 'post'),
    ('/api/v1/articles/{id}/versions', 'post'),
    ('/api/v1/comments/', 'post'),
    ('/api/v1/categories/', 'post'),
    ('/api/v1/tags/', 'post'),
]

# Public paths explicit security override if not set (补充 sitemap/robots)
PUBLIC_PREFIXES = [
    '/api/v1/articles/public', '/api/v1/search/', '/api/v1/users/public', '/api/v1/meta/', '/api/v1/ping', '/api/v1/health', '/sitemap.xml', '/robots.txt'
]

# 统一补全缺失的 2xx 响应 description
# ==== 单次后处理幂等保护 ==== 
# （清理：替换原先空循环占位逻辑，集中到函数 _apply_openapi_post_processing）

def _apply_openapi_post_processing():
    if globals().get('_OPENAPI_POST_PROCESSED'):
        print('[OpenAPI][post] 已跳过（已处理）')
        return
    try:
        print('[OpenAPI][post] 开始执行后处理')
        # ===== 字段约束补充 =====
        def _upd(schema_name, field, **kwargs):
            sch = SCHEMAS.get(schema_name)
            if not sch:
                print(f'[OpenAPI][post] Schema 不存在: {schema_name}')
                return
            props = sch.get('properties', {})
            if field not in props:
                print(f'[OpenAPI][post] 字段缺失: {schema_name}.{field}')
                return
            for k, v in kwargs.items():
                if k not in props[field]:
                    props[field][k] = v
        # 文章
        for s in ('ArticleCreate','ArticleUpdate'):
            _upd(s, 'title', minLength=1, maxLength=120, description='标题 (1-120 字)')
            _upd(s, 'slug', pattern='^[a-z0-9-]+$', minLength=1, maxLength=150, description='URL slug，允许小写字母/数字/连字符')
            _upd(s, 'summary', maxLength=300, description='摘要，<=300 字符')
            _upd(s, 'content_md', minLength=1, description='Markdown 正文')
            _upd(s, 'seo_title', maxLength=120)
            _upd(s, 'seo_desc', maxLength=180)
        print('[OpenAPI][post] 已补充文章字段约束')
        # 分类 / 标签
        for s in ('TagCreate','CategoryCreate','TagUpdate','CategoryUpdate'):
            _upd(s, 'name', minLength=1, maxLength=50, description='名称 (1-50 字)')
            _upd(s, 'slug', pattern='^[a-z0-9-]+$', minLength=1, maxLength=100)
        # 评论
        for s in ('CommentCreate',):
            _upd(s, 'content', minLength=1, maxLength=500, description='评论内容 (1-500 字)')
        print('[OpenAPI][post] 已补充分类/标签/评论字段约束')

        # ===== 枚举补充 =====
        try:
            status_prop = SCHEMAS['ArticleSummary']['properties']['status']
            status_prop.setdefault('enum', ['draft','pending_review','rejected','scheduled','published','archived'])
            filters_props = SCHEMAS['SearchResultResponse']['properties']['data']['allOf'][1]['properties']['filters']['properties']
            if 'status' in filters_props:
                filters_props['status'].setdefault('enum', status_prop['enum'])
            if 'match_mode' in filters_props:
                filters_props['match_mode'].setdefault('enum', ['default','all','any','exact'])
            if 'sort' in filters_props:
                filters_props['sort'].setdefault('enum', ['published_at_desc','published_at_asc','score_desc','views_desc'])
        except Exception as e:
            print('[OpenAPI][post] 枚举补充异常', e)
        if 'CommentModerate' in SCHEMAS:
            SCHEMAS['CommentModerate']['properties']['action'].setdefault('enum', ['approve','reject'])
        if 'BookmarkToggleResponse' in SCHEMAS:
            SCHEMAS['BookmarkToggleResponse']['properties']['data']['properties']['action'].setdefault('enum', ['bookmarked','removed'])
        if 'LikeToggleResponse' in SCHEMAS:
            SCHEMAS['LikeToggleResponse']['properties']['data']['properties']['action'].setdefault('enum', ['liked','unliked'])
        print('[OpenAPI][post] 已补充枚举')

        # ===== 自动标签 =====
        verbs = ('get','post','put','delete','patch')
        tagged = 0
        for path, cfg in PATHS.items():
            for prefix, tag in AUTO_TAG_RULES:
                if path.startswith(prefix):
                    for method, op in cfg.items():
                        if method in verbs:
                            tags = op.setdefault('tags', [])
                            if tag not in tags:
                                tags.append(tag)
                                tagged += 1
        print(f'[OpenAPI][post] 自动标签完成, 新增标签次数={tagged}')

        # ===== 创建接口 201 规范 =====
        normalized = 0
        for p, m in CREATE_OPERATION_SIGNATURES:
            if p in PATHS and m in PATHS[p]:
                resp = PATHS[p][m].setdefault('responses', {})
                if '201' not in resp and '200' in resp:
                    resp['201'] = resp.pop('200')
                    normalized += 1
                if '201' in resp and isinstance(resp['201'], dict):
                    resp['201'].setdefault('description', 'Created')
        print(f'[OpenAPI][post] 创建类接口状态码规范化 {normalized} 条')

        # ===== 公共路径安全覆盖 =====
        public_sec = 0
        for path, cfg in PATHS.items():
            if any(path.startswith(pfx) for pfx in PUBLIC_PREFIXES):
                for method, op in cfg.items():
                    if method in verbs and 'security' not in op:
                        op['security'] = []
                        public_sec += 1
        print(f'[OpenAPI][post] 公共路径安全覆盖 {public_sec} 条')

        # ===== 响应描述补全 =====
        filled = 0
        for path, cfg in PATHS.items():
            for method, op in cfg.items():
                if method in verbs:
                    for code, meta in op.get('responses', {}).items():
                        if isinstance(meta, dict) and not meta.get('description'):
                            meta['description'] = '成功' if str(code).startswith('2') else meta.get('description','')
                            filled += 1
        print(f'[OpenAPI][post] 响应描述补全 {filled} 条')

        # ===== 工作流 / 权限 / 错误码 =====
        WORKFLOW_TRANSITIONS = {
            'draft': ['pending_review','archived'],
            'pending_review': ['rejected','published','archived'],
            'rejected': ['draft','pending_review','archived'],
            'scheduled': ['published','archived'],
            'published': ['archived'],
            'archived': []
        }
        ROLE_MATRIX = {
            'articles:create': ['author','editor','admin'],
            'articles:update': ['author','editor','admin'],
            'articles:delete': ['editor','admin'],
            'workflow:submit': ['author','editor','admin'],
            'workflow:approve': ['editor','admin'],
            'workflow:reject': ['editor','admin'],
            'workflow:publish': ['editor','admin'],
            'comments:moderate': ['editor','admin'],
            'taxonomy:manage': ['editor','admin'],
            'users:change_role': ['admin']
        }
        ERROR_CODES = [
            {'code': 0, 'message': 'ok', 'description': '成功'},
            {'code': 1001, 'message': 'validation_error', 'description': '参数校验失败'},
            {'code': 1002, 'message': 'duplicate_resource', 'description': '唯一约束冲突'},
            {'code': 2001, 'message': 'unauthorized', 'description': '未认证或令牌失效'},
            {'code': 2002, 'message': 'forbidden', 'description': '无权限'},
            {'code': 2003, 'message': 'rate_limited', 'description': '触发频率限制'},
            {'code': 3001, 'message': 'workflow_invalid_state', 'description': '当前状态不允许该操作'},
            {'code': 3002, 'message': 'workflow_transition_conflict', 'description': '状态机并发冲突'},
            {'code': 4001, 'message': 'not_found', 'description': '资源不存在'},
            {'code': 5000, 'message': 'internal_error', 'description': '服务器内部错误'}
        ]
        globals()['_OPENAPI_ERROR_CODES'] = ERROR_CODES
        globals()['_OPENAPI_WORKFLOW_TRANSITIONS'] = WORKFLOW_TRANSITIONS
        globals()['_OPENAPI_ROLE_MATRIX'] = ROLE_MATRIX
        globals()['_OPENAPI_POST_PROCESSED'] = True
        print('[OpenAPI][post] 元数据注入完成')
        logging.info('OpenAPI post-processing completed.')
    except Exception:
        tb = traceback.format_exc()
        logging.error('OpenAPI post-processing failed: %s', tb)
        globals()['_OPENAPI_POST_PROCESS_ERROR'] = tb
        print('[OpenAPI][post] 失败:\n', tb)

# 执行后处理
_apply_openapi_post_processing()

# 重写 assemble_spec 以包含扩展
def assemble_spec():
    try:
        print('[OpenAPI][assemble] 开始组装')
        base = {
            'openapi': '3.0.3',
            'info': {'title': 'Blog API', 'version': '1.0.0'},
            'paths': PATHS,
            'components': {
                'schemas': SCHEMAS,
                'responses': RESPONSES,
                'securitySchemes': {
                    'BearerAuth': {'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT'}
                }
            },
            'security': [{'BearerAuth': []}],
            'tags': [
                {'name': 'auth'},
                {'name': 'users'},
                {'name': 'articles'},
                {'name': 'bookmarks'},
                {'name': 'workflow'},
                {'name': 'versions'},
                {'name': 'search'},
                {'name': 'comments'},
                {'name': 'audit'},
                {'name': 'uploads'},
                {'name': 'taxonomy'},
                {'name': 'meta'}
            ]
        }
        if globals().get('_OPENAPI_ERROR_CODES'):
            base['x-error-codes'] = globals()['_OPENAPI_ERROR_CODES']
            print('[OpenAPI][assemble] 注入 error codes', len(base['x-error-codes']))
        if globals().get('_OPENAPI_WORKFLOW_TRANSITIONS'):
            base['x-workflow-transitions'] = globals()['_OPENAPI_WORKFLOW_TRANSITIONS']
            print('[OpenAPI][assemble] 注入 workflow transitions')
        if globals().get('_OPENAPI_ROLE_MATRIX'):
            base['x-role-matrix'] = globals()['_OPENAPI_ROLE_MATRIX']
            print('[OpenAPI][assemble] 注入 role matrix', len(base['x-role-matrix']))
        if globals().get('_OPENAPI_POST_PROCESS_ERROR'):
            base['x-post-process-error'] = globals()['_OPENAPI_POST_PROCESS_ERROR']
            print('[OpenAPI][assemble] 警告: 存在后处理错误')
        print('[OpenAPI][assemble] 完成')
        return base
    except Exception:
        tb = traceback.format_exc()
        logging.error('assemble_spec failed: %s', tb)
        print('[OpenAPI][assemble] 失败:\n', tb)
        return {'openapi':'3.0.3','info':{'title':'Blog API','version':'1.0.0'},'error': 'assemble_failed'}

OPENAPI_SPEC = assemble_spec()
# 离线快照写入 (供前端 fallback)
try:
    import os, json as _json
    _backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    _target_file = os.path.join(_backend_root, 'openapi.json')
    with open(_target_file, 'w', encoding='utf-8') as f:
        _json.dump(OPENAPI_SPEC, f, ensure_ascii=False, indent=2)
    print(f'[OpenAPI][snapshot] 写入 {_target_file}')
except Exception as _e:
    print('[OpenAPI][snapshot] 写入失败', _e)

@openapi_bp.route('/spec')
def spec():
    return jsonify(OPENAPI_SPEC)

@openapi_bp.route('/spec/debug')
def spec_debug():
    return jsonify({
        'post_processed': bool(globals().get('_OPENAPI_POST_PROCESSED')),
        'post_process_error': globals().get('_OPENAPI_POST_PROCESS_ERROR'),
        'has_error_codes': bool(globals().get('_OPENAPI_ERROR_CODES')),
        'has_role_matrix': bool(globals().get('_OPENAPI_ROLE_MATRIX')),
        'paths_count': len(PATHS),
    })
