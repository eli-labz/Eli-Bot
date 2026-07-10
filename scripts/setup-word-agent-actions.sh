#!/usr/bin/env bash
set -euo pipefail

echo "== Microsoft Word WINWORD.EXE AI Agent Action Integration =="

if [ ! -d ".git" ]; then
  echo "Warning: .git directory not found. Continue only if this is the repo root."
else
  git checkout -b feature/word-winword-action-adapter 2>/dev/null || git checkout feature/word-winword-action-adapter
fi

echo "Detecting project structure..."

if [ -f "package.json" ]; then
  STACK="node"
elif [ -f "pyproject.toml" ] || [ -f "requirements.txt" ]; then
  STACK="python"
elif [ -f "pom.xml" ]; then
  STACK="java-maven"
elif [ -f "build.gradle" ] || [ -f "build.gradle.kts" ]; then
  STACK="java-gradle"
else
  STACK="unknown"
fi

echo "Detected stack: ${STACK}"

mkdir -p core/edge_actions/word
mkdir -p tests/edge_actions
mkdir -p docs/agent-actions
mkdir -p scripts

for file in \
  core/edge_actions/word/word_action_tokens.py \
  core/edge_actions/word/word_observation_adapter.py \
  core/edge_actions/word/word_action_registry.py \
  core/edge_actions/word/word_policy_gate.py \
  core/edge_actions/word/word_action_executor.py \
  core/edge_actions/word/word_outcome_verifier.py \
  core/edge_actions/word/word_trace_writer.py \
  core/edge_actions/word/word_integration.py \
  tests/edge_actions/test_word_integration.py \
  docs/agent-actions/microsoft-word-winword-actions.md
  do
  if [ -f "$file" ]; then
    echo "Detected: $file"
  else
    echo "Creating placeholder: $file"
    cat > "$file" <<'EOF'
# placeholder
EOF
  fi
done

echo "Created or confirmed Word agent directories and documentation."

case "${STACK}" in
  node)
    echo "Running Node checks if available..."
    npm install
    npm run lint --if-present
    npm run typecheck --if-present
    npm test --if-present
    ;;
  python)
    echo "Running Python checks if available..."
    python -m pip install -r requirements.txt 2>/dev/null || true
    python -m pytest tests/edge_actions/test_word_integration.py 2>/dev/null || true
    ;;
  java-maven)
    echo "Running Maven checks..."
    mvn test
    ;;
  java-gradle)
    echo "Running Gradle checks..."
    ./gradlew test
    ;;
  *)
    echo "Unknown stack. Skipping automated checks."
    ;;
esac

echo "Next steps:"
echo "1. Implement WordObservationAdapter."
echo "2. Implement WordActionRegistry."
echo "3. Implement WordPolicyGate."
echo "4. Implement WordActionExecutor."
echo "5. Implement WordOutcomeVerifier."
echo "6. Implement WordTraceWriter."
echo "7. Add integration tests using mocked WINWORD.EXE state."
echo "8. Add human approval tests for risky Word actions."

echo "Microsoft Word modules detected/created:"
find core/edge_actions/word -maxdepth 1 -type f | sort

echo "Done."
