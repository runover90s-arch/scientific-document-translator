from app.core.jobs import JobRecord


def test_public_job_does_not_expose_local_paths():
    job = JobRecord(id="abc", outputs={"pdf": "/srv/private/jobs/abc/output/translated.pdf"})
    public = job.to_public_dict()
    assert public["outputs"]["pdf"] == "/api/v1/jobs/abc/download/pdf"
    assert "/srv/private" not in str(public)


def test_parsed_document_json_hides_source_directory():
    from app.core.models import ParsedDocument

    doc = ParsedDocument(source_path="/srv/private/jobs/abc/input/paper.pdf", blocks=[], parser="test")
    public = doc.to_dict()
    assert public["source_path"] == "paper.pdf"
    assert "/srv/private" not in str(public)
