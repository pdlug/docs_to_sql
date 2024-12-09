# Unstructured documents to SQL(ite) tables

💥 Query your documents with SQL using the power of LLMs!

Small proof of concept using [Instructor](https://python.useinstructor.com/) to extract structured data
from documents and build a [SQLite](https://www.sqlite.org/) table with the
results.

The meat of this is a Pydantic model to SQLite schema generator. It handles most
Pydantic types but has not be extensively tested so you may encounter some edge
cases. Feel free to open an issue if you do.

# Installation

```bash
uv sync
```

Create a `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

# Usage

For a practical example, let's say we want to analyze job postings at OpenAI so we can see who they're hiring or what we need to do to get a job there. The `examples/openai_job_postings` folder contains 85 job postings from the [OpenAI careers](https://openai.com/careers/search/) page. Nothing fancy there, I just copy and pasted the job ad text.

Running the example will load each job posting and insert the result into the database. This will take a bit depending on how fast GPT-4o is today.

```shell
uv run src/docs_to_sql/main.py
```

The output will be a SQLite database named 'job_postings.db' with the extracted job postings in a table called `job_postings`.

## Details

The basic steps are below. I'll skip some details to keep it readable, see `src/docs_to_sql/main.py` for the full code.

To use Instructor, we need to define a Pydantic model that represents the data we want to extract:

```python
class JobPosting(BaseModel):
    minimumSalaryRange: Optional[int]
    maximumSalaryRange: Optional[int]
    jobTitle: str
    companyName: str
    department: Optional[str]
    description: Optional[str]
    requirements: list[str]
    responsibilities: list[str]
    location: Optional[str]
    datePosted: Optional[str]
```

Primitive types like `str`, `int`, `float`, `bool` and `datetime` are mapped to SQLite types. Nested data types like `list` and `dict` are mapped to JSON. The `Optional` type controls whether a `NOT NULL` constraint will be added to the column.

The basic fields above work but we can do a little better by providing some more specific ones for the LLM to extract. If we add a `description` it will show up in the JSON schema passed t othe LLM and provide further instructions. Let's add a `requiredSkills` field that will be extracted as a list of strings and a `locationType` field that's a string enum.

```python
class JobPosting(BaseModel):
    # ...
    requiredSkills: list[str] = Field(
        description="Required skills for the job, mention as individual technologies, tools, languages, skills needed")
    locationType: Literal["onsite", "remote", "hybrid", "unknown"]
```

Then we can create a SQLite database and a table to store the data. The table structure will be generated from the Pydantic model:

```python
import sqlite3
from docs_to_sql.sql import create_table

conn = sqlite3.connect("job_postings.db")
c = conn.cursor()

c.execute(create_table(JobPosting, "job_postings"))
conn.commit()
```

The extract function takes the Pydantic model, a system prompt for some context, and the content to extract the data from.

```python
from docs_to_sql.extract import extract

job_posting = extract(JobPosting, "Analyze the job posting", f.read())
print(job_posting)
```

All we have to do now is insert the data into the database:

```python
from docs_to_sql.sql import insert

insert(c, job_posting, "job_postings")
conn.commit()
```

# Exploration

Now that the magical LLM has turned our unstructured data into a SQL table we can leverage our own magical SQL skills to use it.

We can do simple things like finding out which jobs pay the most:

```sql
SELECT jobTitle, maximumSalaryRange
FROM job_postings
ORDER BY maximumSalaryRange DESC
LIMIT 5;
```

Or any complicated thing we can dream up. For the nested data types we can use SQLite's JSON functions to manipulate them further. For example, which jobs require Python:

```sql
SELECT jobTitle
FROM job_postings, json_each(requiredSkills)
WHERE json_each.value LIKE '%python%';
```

# Notes and credits

Many configs taken from
[python-boilerplate](https://github.com/smarlhens/python-boilerplate)
