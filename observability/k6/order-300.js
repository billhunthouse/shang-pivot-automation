/**
 * 下单接口 300 并发突刺。
 *
 * 设计：
 * - 300 个独立账号（每个账号一个 token + 默认地址），避免购物车/订单互相干扰；
 * - per-vu-iterations：300 VU 同时起跑，每个 VU 只提交 1 次 POST /api/orders；
 * - 只压下单接口，不支付，避免支付链路干扰；
 * - 账号数据由 scripts 生成到 data/order-users-300.json（token 15 分钟有效）。
 *
 * 运行：
 *   k6 run -o experimental-prometheus-rw \
 *     --tag app=shang-pivot --tag env=local-perf --tag scenario=order-300 \
 *     -e BASE_URL=http://127.0.0.1:8086/api \
 *     -e SKU_ID=10012 \
 *     observability/k6/order-300.js
 */
import http from 'k6/http';
import { check } from 'k6';
import { Counter, Trend } from 'k6/metrics';
import { jsonHeaders, parseJson, isBusinessSuccess } from './lib/shang.js';

const users = JSON.parse(open('./data/order-users-300.json'));
const VUS = Number(__ENV.VUS || 300);
const SKU_ID = __ENV.SKU_ID || '10012';

const orderDuration = new Trend('order_submit_duration', true);
const orderSuccess = new Counter('order_success_total');
const orderFailed = new Counter('order_failed_total');

export const options = {
  scenarios: {
    order_burst: {
      executor: 'per-vu-iterations',
      vus: VUS,
      iterations: 1,
      maxDuration: '3m',
    },
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

export function setup() {
  if (users.length < VUS) {
    throw new Error(`账号不足：需要 ${VUS}，实际 ${users.length}`);
  }
  return {
    baseUrl: (__ENV.BASE_URL || 'http://127.0.0.1:8086/api').replace(/\/+$/, ''),
    users: users.slice(0, VUS),
    skuId: SKU_ID,
  };
}

export default function (data) {
  const user = data.users[__VU - 1];
  const idempotentKey = `k6-order-300-${__VU}-${__ITER}-${Date.now()}`;
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

  if (ok) {
    orderSuccess.add(1);
  } else {
    orderFailed.add(1);
    console.log(`order failed vu=${__VU} status=${response.status} body=${String(response.body).slice(0, 200)}`);
  }
}
