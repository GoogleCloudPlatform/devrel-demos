/*
 * Copyright 2022 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.google.beam.workshop;

import org.apache.beam.sdk.Pipeline;
import org.apache.beam.sdk.schemas.Schema;
import org.apache.beam.sdk.testing.PAssert;
import org.apache.beam.sdk.testing.TestPipeline;
import org.apache.beam.sdk.transforms.Create;
import org.apache.beam.sdk.values.PCollection;
import org.apache.beam.sdk.values.Row;
import org.junit.Rule;
import org.junit.Test;

public class FieldPrefixAdderTransformTest {

  @Rule
  public final transient TestPipeline pipeline = TestPipeline.create();

  static Schema schema = Schema.builder()
      .addStringField("a")
      .addStringField("b")
      .build();

  private static Row row(String aValue, String bValue) {
    return Row.withSchema(schema).withFieldValue("a", aValue).withFieldValue("b", bValue).build();
  }

  @Test
  public void testTransform() {
    Pipeline pipeline = Pipeline.create();
    PCollection<Row> rows = pipeline.apply("Create Rows", Create.of(
        row("1", "2"),
        row("3", "4")
        )).setRowSchema(schema);

    PCollection<Row> prefixedRows = rows.apply("Add Prefix",  FieldPrefixAdderTransform.create("a", "--"));
    PAssert.that(prefixedRows).containsInAnyOrder(
        row("--1", "2"),
        row("--3", "4"));

    PCollection<Row> nonPrefixedRows = rows.apply("Attempt to Prefix",  FieldPrefixAdderTransform.create("unrecognized prefix", "--"));
    PAssert.that(nonPrefixedRows).containsInAnyOrder(
        // Original rows
        row("1", "2"),
        row("3", "4"));

    pipeline.run().waitUntilFinish();
  }

}