import test from 'node:test';
import assert from 'node:assert/strict';
import install from '../scripts/pi-workbench.mjs';

test('lab context follows session state and leaves input text unchanged', async () => {
  process.env.WORKBENCH_MODE = 'apk';
  process.env.WORKBENCH_ROOT = 'C:/test';
  const events = {}, commands = {};
  install({ on: (name, handler) => { events[name] = handler; },
    registerCommand: (name, command) => { commands[name] = command; } });
  const ctx = {hasUI: false}, event = {systemPrompt: 'PI built-in prompt'};
  await events.session_start();
  assert.match((await events.before_agent_start(event)).systemPrompt, /尚未开启/);
  assert.deepEqual(await events.input({text: 'Analyze test.apk'}, ctx), {action: 'continue'});
  assert.deepEqual(await events.input({text: 'lab：'}, ctx), {action: 'handled'});
  assert.match((await events.before_agent_start(event)).systemPrompt, /^PI built-in prompt\n\n当前独立工作台：apk/);
  await events.input({text: '退出实验'}, ctx);
  assert.match((await events.before_agent_start(event)).systemPrompt, /尚未开启/);
  await commands.lab.handler('', ctx);
  assert.doesNotMatch((await events.before_agent_start(event)).systemPrompt, /尚未开启/);
  await events.session_start();
  assert.match((await events.before_agent_start(event)).systemPrompt, /尚未开启/);
  process.env.WORKBENCH_MODE = 'coding';
  assert.equal(await events.before_agent_start(event), undefined);
  assert.deepEqual(await events.input({text: 'lab：'}, ctx), {action: 'continue'});
});
