"""Celery tasks for workflow management."""

from celery import current_app as celery_app
from document_forensics.workflow.workflow_manager import WorkflowManager


@celery_app.task(bind=True)
def process_document_workflow(self, document_id: str, workflow_config: dict):
    """Process a complete document analysis workflow."""
    try:
        manager = WorkflowManager()
        result = manager.execute_workflow(document_id, workflow_config)
        return {
            "document_id": document_id,
            "workflow_result": result.dict(),
            "status": "completed"
        }
    except Exception as exc:
        self.retry(exc=exc, countdown=60, max_retries=3)


@celery_app.task(bind=True)
def batch_process_documents(self, document_ids: list, workflow_config: dict):
    """Process multiple documents in batch."""
    try:
        manager = WorkflowManager()
        results = []
        for doc_id in document_ids:
            result = manager.execute_workflow(doc_id, workflow_config)
            results.append({
                "document_id": doc_id,
                "result": result.dict()
            })
        return {
            "batch_results": results,
            "status": "completed"
        }
    except Exception as exc:
        self.retry(exc=exc, countdown=60, max_retries=3)