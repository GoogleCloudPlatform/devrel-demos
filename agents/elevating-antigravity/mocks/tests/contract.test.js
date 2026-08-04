/**
Copyright 2026 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/
import test from 'node:test';
import assert from 'node:assert/strict';

const delay = (ms = 180) => new Promise((res) => setTimeout(res, ms));

// NOTE: This test suite contains an intentional failure used to demonstrate multi-agent
// parallel test execution and diagnostic reporting for the batch-executing-test-suites skill.
test('API Contract Suite: Microservice REST Endpoint Schemas', async (t) => {
  await t.test('GET /api/v2/users/101 schema validation', async () => {
    await delay();
    const mockResponse = {
      id: 101,
      name: 'Alice Smith',
      email: 'alice@domain.org',
      status: 'ACTIVE',
      roles: ['ADMIN', 'USER']
    };

    assert.equal(typeof mockResponse.id, 'number');
    assert.equal(typeof mockResponse.name, 'string');
    assert.equal(typeof mockResponse.email, 'string');
    assert.equal(Array.isArray(mockResponse.roles), true);
  });

  await t.test('GET /api/v2/products paginated list schema', async () => {
    await delay();
    const mockResponse = {
      data: [{ id: 'prod_1', name: 'Widget A', price: 29.99 }],
      page: 1,
      pageSize: 20,
      totalCount: 1
    };

    assert.equal(Array.isArray(mockResponse.data), true);
    assert.equal(typeof mockResponse.page, 'number');
    assert.equal(typeof mockResponse.totalCount, 'number');
  });

  // INTENTIONAL FAILURE SUITE:
  // This subtest intentionally fails due to a missing 'paymentMethod' property on the order response payload.
  // It provides stack trace data for testing diagnostic failure handling by parallel subagent test runners.
  await t.test('POST /api/v2/orders schema validation', async () => {
    await delay();
    const mockResponse = {
      orderId: 'ord_9982',
      amount: 150.00,
      currency: 'USD',
      status: 'PENDING'
    };

    // Intentional contract failure for diagnostic testing: expected payload field 'paymentMethod'
    assert.ok(mockResponse.paymentMethod, 'Contract Violation: Response payload missing required field "paymentMethod"');
  });

  await t.test('POST /api/v2/auth/token OAuth2 response schema', async () => {
    await delay();
    const mockResponse = {
      access_token: 'jwt_mock_header.payload.sig',
      token_type: 'Bearer',
      expires_in: 3600
    };

    assert.equal(typeof mockResponse.access_token, 'string');
    assert.equal(mockResponse.token_type, 'Bearer');
    assert.equal(typeof mockResponse.expires_in, 'number');
  });

  await t.test('GET /api/v2/analytics/metrics response schema', async () => {
    await delay();
    const mockResponse = {
      metric: 'http_requests_total',
      value: 14022,
      timestamp: Date.now()
    };

    assert.equal(typeof mockResponse.metric, 'string');
    assert.equal(typeof mockResponse.value, 'number');
  });
});
