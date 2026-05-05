# Drug/Product Name Search Service

🚀 Backend FastAPI sử dụng SQLite để import dữ liệu sản phẩm crawl từ Chiaki.vn và tìm kiếm theo tên, mô tả, comment. 
- ✅ Hỗ trợ tiếng Việt không dấu
- ✅ Fuzzy search khi người dùng gõ sai
- ✅ 400+ sản phẩm + 2000+ comments

## Cấu trúc thư mục

```text
Mini_pj/
├── app/
│   ├── main.py                          # FastAPI app
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py                    # Settings từ .env
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py                      # Import models
│   │   └── session.py                   # SQLAlchemy setup + get_db()
│   ├── models/
│   │   ├── __init__.py
│   │   └── product.py                   # Product + Comment models
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── product.py                   # Pydantic schemas
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── product_repository.py        # Database queries
│   ├── services/
│   │   ├── __init__.py
│   │   ├── text_normalizer.py           # Remove accents, normalize
│   │   └── search_service.py            # Basic + fuzzy search
│   └── api/
│       ├── __init__.py
│       └── v1/
│           ├── __init__.py
│           ├── router.py                # Include routers
│           └── product_routes.py        # API endpoints
├── scripts/
│   ├── __init__.py
│   ├── create_tables.py                 # Create database schema
│   └── import_products.py               # Import data từ JSON
├── data/
│   └── medicine_search.db               # SQLite database (auto-created)
├── chiaki_products.json                 # Input data
├── requirements.txt                     # Dependencies
├── .env                                 # Environment variables
└── README.md                            # This file
```

## Cài đặt nhanh

```bash
# 1. Chuyển vào thư mục
cd d:\TRAINING_NLP_RPG\Mini_pj

# 2. Cài đặt dependencies
pip install -r requirements.txt

# 3. Tạo database tables
python -m scripts.create_tables

# 4. Import dữ liệu
python -m scripts.import_products

# 5. Chạy API server
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Features

### 1. Text Normalization
Chuyển đổi text tiếng Việt có dấu thành không dấu:
```
"Viên Bổ Gan" → "vien bo gan"
"Vitamin Đ" → "vitamin d"
"SANG!!!????" → "sang"
```

### 2. Search Cơ Bản (Basic Search)
Tìm kiếm trong:
- `normalized_name` - tên sản phẩm
- `normalized_description` - mô tả
- `normalized_content` - nội dung comment

Score: 100 (exact match) → 70 (partial)

### 3. Fuzzy Search
Sử dụng `rapidfuzz` để tìm khi người dùng gõ sai:
- `vitmin` → tìm được `vitamin`
- `gan` → tìm được trong `giảm cân`

Score: 76-100

### 4. Search Results
Kết quả được sắp xếp theo:
1. Score cao nhất trước
2. Tên sản phẩm (A-Z)

Mỗi result có:
```json
{
  "id": 1,
  "name": "...",
  "url": "...",
  "description": "...",
  "category": "...",
  "price": "...",
  "source": "chiaki.vn",
  "score": 100.0,
  "match_type": "basic"  // or "fuzzy"
}
```

## Database Schema

### products table
```sql
- id (INTEGER, PK)
- name (STRING, indexed)
- normalized_name (STRING, indexed)
- url (STRING, unique)
- description (TEXT)
- normalized_description (TEXT)
- category (STRING, indexed)
- price (STRING)
- source (STRING, default: chiaki.vn)
- created_at (DATETIME)
- comments (one-to-many relationship)
```

### comments table
```sql
- id (INTEGER, PK)
- product_id (INTEGER, FK→products)
- author (VARCHAR, nullable)
- rating (INTEGER, nullable)
- content (TEXT)
- normalized_content (TEXT, indexed)
- date (VARCHAR, nullable)
```

Nếu database PostgreSQL đã tồn tại từ schema cũ, thêm cột trước khi import lại:
```sql
ALTER TABLE comments ADD COLUMN IF NOT EXISTS author VARCHAR;
ALTER TABLE comments ADD COLUMN IF NOT EXISTS rating INTEGER;
ALTER TABLE comments ADD COLUMN IF NOT EXISTS date VARCHAR;
```

## API Endpoints

### 1. Health Check
```bash
GET /health

Response 200:
{
  "status": "ok",
  "service": "drug-product-name-search-service"
}
```

### 2. List Products (Pagination)
```bash
GET /api/v1/products/?limit=20&offset=0

Query Parameters:
- limit: int (1-100, default: 20)
- offset: int (≥0, default: 0)

Response 200:
[
  {
    "id": 1,
    "name": "...",
    "url": "...",
    "description": "...",
    "category": "...",
    "price": "...",
    "source": "chiaki.vn",
    "created_at": "2026-05-05T06:55:21.685236"
  },
  ...
]
```

### 3. Get Product Detail
```bash
GET /api/v1/products/{product_id}

Response 200:
{
  "id": 1,
  "name": "...",
  "url": "...",
  "description": "...",
  "category": "...",
  "price": "...",
  "source": "chiaki.vn",
  "created_at": "2026-05-05T06:55:21.685236",
  "comments": [
    {
      "id": 1,
      "author": "La*****09",
      "rating": 5,
      "content": "Dùng 10 ngày bụng nhẹ ghê luôn =)",
      "date": "13:53, 05/04/2026"
    },
    ...
  ]
}
```

Response 404: `{"detail": "Product not found"}`

### 4. Search Products
```bash
GET /api/v1/products/search?q=bo%20gan&limit=10

Query Parameters:
- q: string (min_length: 2, required)
- limit: int (1-50, default: 10)

Response 200:
{
  "query": "bo gan",
  "total": 3,
  "results": [
    {
      "id": 1,
      "name": "...",
      "url": "...",
      "description": "...",
      "category": "...",
      "price": "...",
      "source": "chiaki.vn",
      "comments_count": 10,
      "comments": [
        {
          "id": 1,
          "author": "La*****09",
          "rating": 5,
          "content": "Dùng 10 ngày bụng nhẹ ghê luôn =)",
          "date": "13:53, 05/04/2026"
        }
      ],
      "score": 100.0,
      "match_type": "basic"
    },
    ...
  ]
}
```

## Test API

### Cách 1: Dùng curl
```bash
# Health check
curl http://127.0.0.1:8000/health

# List products
curl "http://127.0.0.1:8000/api/v1/products/?limit=5"

# Get product detail
curl "http://127.0.0.1:8000/api/v1/products/1"

# Search basic
curl "http://127.0.0.1:8000/api/v1/products/search?q=bo%20gan&limit=5"

# Search fuzzy
curl "http://127.0.0.1:8000/api/v1/products/search?q=vitmin&limit=5"
```

### Cách 2: Dùng Python script
```bash
python test_api.py
```

### Cách 3: Dùng Swagger UI
```
http://127.0.0.1:8000/docs
```

## Configuration

File `.env`:
```env
DATABASE_URL=sqlite:///./data/medicine_search.db
```

Để dùng PostgreSQL:

```env
DATABASE_URL=postgresql+psycopg2://postgres:<PASSWORD>@localhost:5432/medicine_search
```

Nếu password có ký tự đặc biệt như `@`, `#`, `:`, `/`, hãy URL-encode password trước khi đưa vào `DATABASE_URL`.

Ví dụ tạo database bằng `psql`:

```bash
psql -U postgres -c "CREATE DATABASE medicine_search;"
```

Sau đó chạy:

```bash
python -m scripts.create_tables
python -m scripts.import_products
```

Trên PowerShell, biến môi trường `DATABASE_URL` trong session hiện tại sẽ override file `.env`. Kiểm tra bằng:

```powershell
echo $env:DATABASE_URL
```

Nếu đang trỏ nhầm DB, xóa biến session:

```powershell
Remove-Item Env:DATABASE_URL
```

## Troubleshooting

### 1. "ModuleNotFoundError: No module named 'app'"
→ Chạy uvicorn từ thư mục Mini_pj
```bash
cd d:\TRAINING_NLP_RPG\Mini_pj
$env:PYTHONPATH="d:\TRAINING_NLP_RPG\Mini_pj"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 2. "No such table: products"
→ Chạy create_tables.py trước
```bash
python -m scripts.create_tables
```

### 3. "password authentication failed for user postgres"
→ PostgreSQL đã nhận kết nối nhưng username/password trong `DATABASE_URL` không đúng.

Kiểm tra `.env`:
```env
DATABASE_URL=postgresql+psycopg2://postgres:<PASSWORD>@localhost:5432/medicine_search
```

Nếu đang dùng PowerShell env var, nó có thể đang override `.env`:
```powershell
echo $env:DATABASE_URL
Remove-Item Env:DATABASE_URL
```

### 4. "database medicine_search does not exist"
→ Tạo database trước rồi mới chạy `create_tables`:
```bash
psql -U postgres -c "CREATE DATABASE medicine_search;"
```

### 5. "Cannot find input file"
→ Đặt file chiaki_products.json vào một trong hai vị trí:
- `Mini_pj/data/chiaki_products.json`
- `Mini_pj/chiaki_products.json`

### 6. Import không update dữ liệu
→ Database sử dụng upsert, nếu sản phẩm đã có URL giống thì update
→ Để reset, xóa file `data/medicine_search.db` và chạy create_tables + import lại

## Performance

- **Database**: SQLite local hoặc PostgreSQL qua SQLAlchemy
- **Indexes**: name, normalized_name, url, category, normalized_description, normalized_content
- **Search**: ~50-100ms (basic), ~200-500ms (fuzzy)
- **Concurrent users**: ∞ (depends on hardware)

## Architecture

```
Request
  ↓
FastAPI Routes (product_routes.py)
  ↓
Dependency Injection (get_db)
  ↓
Repository (ProductRepository)
  ↓ queries
SQLAlchemy ORM
  ↓
SQLAlchemy Database
  ↓
Service Layer (SearchService)
  ↓ text_normalizer
TextNormalizer
  ↓
Response (Pydantic Schema)
```

## Development

### Thêm endpoint mới
1. Thêm hàm trong `app/api/v1/product_routes.py`
2. Define request/response schemas trong `app/schemas/product.py`
3. Thêm business logic trong `SearchService` hoặc repository

### Thay đổi database schema
1. Edit `app/models/product.py`
2. Xóa `data/medicine_search.db`
3. Chạy `python -m scripts.create_tables`
4. Chạy `python -m scripts.import_products` lại

### Tối ưu search
- Điều chỉnh `fuzzy_threshold` trong `SearchService.__init__`
- Điều chỉnh weights trong `_fuzzy_score`
- Thêm more indexes nếu cần

## License

MIT License

## Authors

Senior Python Backend Engineer
May 5, 2026
