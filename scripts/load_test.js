import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8000';
const LOAD_VUS = parseInt(__ENV.LOAD_VUS || '20', 10);
const LOAD_DURATION = __ENV.LOAD_DURATION || '30s';
const LOAD_RAMP_UP = __ENV.LOAD_RAMP_UP || '10s';
const LOAD_RAMP_DOWN = __ENV.LOAD_RAMP_DOWN || '10s';
const LOAD_P95 = __ENV.LOAD_P95 || '500';

export const options = {
  stages: [
    { duration: LOAD_RAMP_UP, target: LOAD_VUS },
    { duration: LOAD_DURATION, target: LOAD_VUS },
    { duration: LOAD_RAMP_DOWN, target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: [`p(95)<${LOAD_P95}`],
  },
};

export default function () {
  const health = http.get(`${BASE_URL}/health`);
  check(health, { 'health 200': (r) => r.status === 200 });

  const tools = http.get(`${BASE_URL}/tools/list?session_id=load`);
  check(tools, { 'tools 200': (r) => r.status === 200 });

  const payload = JSON.stringify({
    session_id: 'load',
    tool_name: 'db_query',
    arguments: { query: 'SELECT 1' },
  });
  const headers = { 'Content-Type': 'application/json' };
  const call = http.post(`${BASE_URL}/tools/call`, payload, { headers });
  check(call, { 'call 200': (r) => r.status === 200 });

  sleep(0.1);
}
