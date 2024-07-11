import sqlite3

from pydantic import BaseModel, Field
import os
from os.path import isfile, join
from typing import Literal, Optional

from docs_to_sql.extract import extract
from docs_to_sql.sql import insert, create_table


class JobPosting(BaseModel):
    minimumSalaryRange: Optional[int]
    maximumSalaryRange: Optional[int]
    jobTitle: str
    companyName: str
    department: Optional[str]
    description: Optional[str]
    requirements: list[str]
    requiredSkills: list[str] = Field(
        description="Required skills for the job, mention as individual technologies, tools, languages, skills needed"
    )
    responsibilities: list[str]
    location: Optional[str]
    datePosted: Optional[str]
    locationType: Literal["onsite", "remote", "hybrid", "unknown"]


def process_job_postings(db_name: str, table_name: str) -> None:
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    create_table_statement = create_table(JobPosting, table_name)

    c.execute(create_table_statement)
    conn.commit()

    job_postings_dir = "./examples/openai_job_postings"
    job_posting_files = [
        f for f in os.listdir(job_postings_dir) if isfile(join(job_postings_dir, f))
    ]

    for job_posting_file in job_posting_files:
        with open(os.path.join(job_postings_dir, job_posting_file), "r") as f:
            print(f"Processing {job_posting_file}")
            job_posting = extract(JobPosting, "Analyze the job posting", f.read())
            insert(c, job_posting, table_name)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    process_job_postings("job_postings.db", "job_postings")
