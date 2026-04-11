// ABOUTME: Unit tests for journal writing functionality
// ABOUTME: Tests file system operations, timestamps, and formatting


import * as fs from 'fs/promises';
import * as path from 'path';
import * as os from 'os';
import { JournalManager } from '../src/journal';

function getFormattedDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

describe('JournalManager', () => {
  let projectTempDir: string;
  let userTempDir: string;
  let journalManager: JournalManager;
  let originalHome: string | undefined;

  beforeEach(async () => {
    projectTempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'journal-project-test-'));
    userTempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'journal-user-test-'));
    
    // Mock HOME environment
    originalHome = process.env.HOME;
    process.env.HOME = userTempDir;
    
    journalManager = new JournalManager(projectTempDir);
  });

  afterEach(async () => {
    // Restore original HOME
    if (originalHome !== undefined) {
      process.env.HOME = originalHome;
    } else {
      delete process.env.HOME;
    }
    
    await fs.rm(projectTempDir, { recursive: true, force: true });
    await fs.rm(userTempDir, { recursive: true, force: true });
  });

  test('writes project notes to project directory', async () => {
    const thoughts = {
      project_notes: 'The architecture is solid'
    };
    
    await journalManager.writeThoughts(thoughts);

    const today = new Date();
    const dateString = getFormattedDate(today);
    const projectDayDir = path.join(projectTempDir, dateString);
    
    const projectFiles = await fs.readdir(projectDayDir);
    expect(projectFiles).toHaveLength(2); // .md and .embedding

    const projectMdFile = projectFiles.find(f => f.endsWith('.md'))!;
    const projectContent = await fs.readFile(path.join(projectDayDir, projectMdFile), 'utf8');

    expect(projectContent).toContain('## Project Notes');
    expect(projectContent).toContain('The architecture is solid');
    expect(projectContent).not.toContain('## Reflections');
  });

  test('writeThoughts produces filenames with microsecond precision', async () => {
    await journalManager.writeThoughts({
      reflections: 'Filename format check'
    });

    const today = new Date();
    const dateString = getFormattedDate(today);
    const userDayDir = path.join(userTempDir, '.private-journal', dateString);
    const userFiles = await fs.readdir(userDayDir);

    const mdFile = userFiles.find(f => f.endsWith('.md'));
    expect(mdFile).toBeDefined();
    expect(mdFile).toMatch(/^\d{2}-\d{2}-\d{2}-\d{6}\.md$/);
  });

  test('writeThoughts emits well-formed YAML frontmatter', async () => {
    await journalManager.writeThoughts({
      reflections: 'Frontmatter shape check'
    });

    const today = new Date();
    const dateString = getFormattedDate(today);
    const userDayDir = path.join(userTempDir, '.private-journal', dateString);
    const userFiles = await fs.readdir(userDayDir);
    const mdFile = userFiles.find(f => f.endsWith('.md'))!;
    const fileContent = await fs.readFile(path.join(userDayDir, mdFile), 'utf8');

    const lines = fileContent.split('\n');
    expect(lines[0]).toBe('---');
    expect(lines[1]).toMatch(/^title: ".*"$/);
    expect(lines[2]).toMatch(/^date: \d{4}-\d{2}-\d{2}T/);
    expect(lines[3]).toMatch(/^timestamp: \d+$/);
    expect(lines[4]).toBe('---');
  });

  test('writeThoughts produces distinct filenames for rapid successive writes', async () => {
    await journalManager.writeThoughts({ reflections: 'First rapid entry' });
    await journalManager.writeThoughts({ reflections: 'Second rapid entry' });

    const today = new Date();
    const dateString = getFormattedDate(today);
    const userDayDir = path.join(userTempDir, '.private-journal', dateString);
    const userFiles = await fs.readdir(userDayDir);

    const mdFiles = userFiles.filter(f => f.endsWith('.md'));
    expect(mdFiles).toHaveLength(2);
    expect(mdFiles[0]).not.toEqual(mdFiles[1]);
  });

  test('writes user thoughts to user directory', async () => {
    const thoughts = {
      reflections: 'I feel great about this feature',
      technical_insights: 'TypeScript interfaces are powerful'
    };

    await journalManager.writeThoughts(thoughts);

    const today = new Date();
    const dateString = getFormattedDate(today);
    const userDayDir = path.join(userTempDir, '.private-journal', dateString);

    const userFiles = await fs.readdir(userDayDir);
    expect(userFiles).toHaveLength(2); // .md and .embedding

    const userMdFile = userFiles.find(f => f.endsWith('.md'))!;
    const userContent = await fs.readFile(path.join(userDayDir, userMdFile), 'utf8');

    expect(userContent).toContain('## Reflections');
    expect(userContent).toContain('I feel great about this feature');
    expect(userContent).toContain('## Technical Insights');
    expect(userContent).toContain('TypeScript interfaces are powerful');
    expect(userContent).not.toContain('## Project Notes');
  });

  test('writes observations to user directory', async () => {
    const thoughts = {
      observations: 'I noticed the test runner caches pycache weirdly'
    };

    await journalManager.writeThoughts(thoughts);

    const today = new Date();
    const dateString = getFormattedDate(today);
    const userDayDir = path.join(userTempDir, '.private-journal', dateString);

    const userFiles = await fs.readdir(userDayDir);
    expect(userFiles).toHaveLength(2); // .md and .embedding

    const userMdFile = userFiles.find(f => f.endsWith('.md'))!;
    const userContent = await fs.readFile(path.join(userDayDir, userMdFile), 'utf8');

    expect(userContent).toContain('## Observations');
    expect(userContent).toContain('I noticed the test runner caches pycache weirdly');
    expect(userContent).not.toContain('## Project Notes');
  });

  test('splits thoughts between project and user directories', async () => {
    const thoughts = {
      reflections: 'I feel great',
      project_notes: 'The architecture is solid',
      user_context: 'Jesse prefers simple solutions',
      technical_insights: 'TypeScript is powerful',
      world_knowledge: 'Git workflows matter'
    };

    await journalManager.writeThoughts(thoughts);

    const today = new Date();
    const dateString = getFormattedDate(today);

    // Check project directory
    const projectDayDir = path.join(projectTempDir, dateString);
    const projectFiles = await fs.readdir(projectDayDir);
    expect(projectFiles).toHaveLength(2); // .md and .embedding

    const projectMdFile = projectFiles.find(f => f.endsWith('.md'))!;
    const projectContent = await fs.readFile(path.join(projectDayDir, projectMdFile), 'utf8');
    expect(projectContent).toContain('## Project Notes');
    expect(projectContent).toContain('The architecture is solid');
    expect(projectContent).not.toContain('## Reflections');

    // Check user directory
    const userDayDir = path.join(userTempDir, '.private-journal', dateString);
    const userFiles = await fs.readdir(userDayDir);
    expect(userFiles).toHaveLength(2); // .md and .embedding

    const userMdFile = userFiles.find(f => f.endsWith('.md'))!;
    const userContent = await fs.readFile(path.join(userDayDir, userMdFile), 'utf8');
    expect(userContent).toContain('## Reflections');
    expect(userContent).toContain('## User Context');
    expect(userContent).toContain('## Technical Insights');
    expect(userContent).toContain('## World Knowledge');
    expect(userContent).not.toContain('## Project Notes');
  });

  test('handles thoughts with only user sections', async () => {
    const thoughts = {
      world_knowledge: 'Learned something interesting about databases'
    };
    
    await journalManager.writeThoughts(thoughts);

    const today = new Date();
    const dateString = getFormattedDate(today);
    
    // Should only create user directory, not project directory
    const userDayDir = path.join(userTempDir, '.private-journal', dateString);
    const userFiles = await fs.readdir(userDayDir);
    expect(userFiles).toHaveLength(2); // .md and .embedding

    const userMdFile = userFiles.find(f => f.endsWith('.md'))!;
    const userContent = await fs.readFile(path.join(userDayDir, userMdFile), 'utf8');
    expect(userContent).toContain('## World Knowledge');
    expect(userContent).toContain('Learned something interesting about databases');
    
    // Project directory should not exist
    const projectDayDir = path.join(projectTempDir, dateString);
    await expect(fs.access(projectDayDir)).rejects.toThrow();
  });

  test('handles thoughts with only project sections', async () => {
    const thoughts = {
      project_notes: 'This specific codebase pattern works well'
    };
    
    await journalManager.writeThoughts(thoughts);

    const today = new Date();
    const dateString = getFormattedDate(today);
    
    // Should only create project directory, not user directory
    const projectDayDir = path.join(projectTempDir, dateString);
    const projectFiles = await fs.readdir(projectDayDir);
    expect(projectFiles).toHaveLength(2); // .md and .embedding

    const projectMdFile = projectFiles.find(f => f.endsWith('.md'))!;
    const projectContent = await fs.readFile(path.join(projectDayDir, projectMdFile), 'utf8');
    expect(projectContent).toContain('## Project Notes');
    expect(projectContent).toContain('This specific codebase pattern works well');
    
    // User directory should not exist
    const userDayDir = path.join(userTempDir, '.private-journal', dateString);
    await expect(fs.access(userDayDir)).rejects.toThrow();
  });

  test('uses explicit user journal path when provided', async () => {
    const customUserDir = await fs.mkdtemp(path.join(os.tmpdir(), 'custom-user-'));
    const customJournalManager = new JournalManager(projectTempDir, customUserDir);
    
    try {
      const thoughts = { reflections: 'Testing custom path' };
      await customJournalManager.writeThoughts(thoughts);

      const today = new Date();
      const dateString = getFormattedDate(today);
      const customDayDir = path.join(customUserDir, dateString);
      
      const customFiles = await fs.readdir(customDayDir);
      expect(customFiles).toHaveLength(2); // .md and .embedding

      const customMdFile = customFiles.find(f => f.endsWith('.md'))!;
      const customContent = await fs.readFile(path.join(customDayDir, customMdFile), 'utf8');
      expect(customContent).toContain('Testing custom path');
    } finally {
      await fs.rm(customUserDir, { recursive: true, force: true });
    }
  });
});