/**
 * 下单接口 300 并发持续负载。
 *
 * 与 order-300.js 的区别：
 * - order-300.js 是 300 VU 一次性突刺（每个 VU 1 次）；
 * - 本脚本是 300 VU 持续 20s（每 VU 循环下单），用于让 Prometheus 5s 抓取窗口
 *   能观察到 HikariCP / Tomcat / PostgreSQL 的真实排队情况。
 *
 * 运行：
 *   k6 run -o experimental-prometheus-rw \
 *     --tag app=shang-pivot --tag env=local-perf --tag scenario=order-300-load \
 *     -e BASE_URL=http://127.0.0.1:8086/api -e SKU_ID=10012 -e VUS=300 -e DURATION=20s \
 *     observability/k6/order-300-sustained.js
 */
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';
import { jsonHeaders, parseJson, isBusinessSuccess } from './lib/shang.js';

const users = JSON.parse(open('./data/order-users-300.json'));
const VUS = Number(__ENV.VUS || 300);
const DURATION = __ENV.DURATION || '20s';
const SKU_ID = __ENV.SKU_ID || '10012';
const THINK = Number(__ENV.THINK_TIME || 0.5);

const orderDuration = new Trend('order_submit_duration', true);
const orderSuccess = new Counter('order_success_total');
const orderFailed = new Counter('order_failed_total');

export const options = {
  scenarios: {
    order_load: {
      executor: 'constant-vus',
      vus: VUS,
      duration: DURATION,
      gracefulStop: '10s',
    },
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

export function setup() {
  if (users.length < VUS) throw new Error(`账号不足：需要 ${VUS}，实际 ${users.length}`);
  return {
    baseUrl: (__ENV.BASE_URL || 'http://127.0.0.1:8086/api').replace(/\/+$/, ''),
    users: users.slice(0, VUS),
    skuId: SKU_ID,
  };
}

export default function (data) {
  const user = data.users[__VU - 1];
  const idempotentKey = `k6-order-300-load-${__VU}-${__ITER}-${Date.now()}`;
  const response = http.post(
    `${data.baseUrl}/orders`,
    JSON.stringify({
      addressId: user.addressId,
      skuId: data.skuId,
      quantity: 1,
      idempotentKey,
    }),
    { ...jsonHeaders(user.token), tags: { endpoint: 'order_submit' } },
  );

  orderDuration.add(response.timings.duration);
  const body = parseJson(response);
  const ok = check(response, {
    'order HTTP 200': (res) => res.status === 200,
    'order business code 0': () => isBusinessSuccess(body),
  });
  if (ok) orderSuccess.add(1);
  else {
    orderFailed.add(1);
    console.log(`order failed vu=${__VU} status=${response.status} body=${String(response.body).slice(0, 200)}`);
  }
  sleep(THINK);
}
