"""Compatibilité — préférez tools.codegen_service."""

from tools.codegen_service import (
    CodeGenComplexity,
    CodeGenService,
    CodeGenServiceError,
    CodeGenerateResult,
    GeneratedFile,
    complexity_from_score,
)

# Alias historiques
ClaudeService = CodeGenService
ClaudeServiceError = CodeGenServiceError
ClaudeCodeResult = CodeGenerateResult
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-20250514"
