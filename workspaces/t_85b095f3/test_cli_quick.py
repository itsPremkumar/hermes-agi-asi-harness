"""Quick CLI test."""
from click.testing import CliRunner
from agentos.cli import main

runner = CliRunner()

# Test version
result = runner.invoke(main, ['--version'])
print('Version test:')
print('  exit:', result.exit_code)
print('  output:', repr(result.output))
print()

# Test status
result = runner.invoke(main, ['status'])
print('Status test:')
print('  exit:', result.exit_code)
print('  output:', repr(result.output[:100]))
print()

# Test self-test
result = runner.invoke(main, ['self-test'])
print('Self-test:')
print('  exit:', result.exit_code)
print('  output:', repr(result.output[:200]))
