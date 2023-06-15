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

import org.apache.beam.sdk.schemas.Schema;
import org.apache.beam.sdk.transforms.DoFn;
import org.apache.beam.sdk.transforms.PTransform;
import org.apache.beam.sdk.transforms.ParDo;
import org.apache.beam.sdk.values.PCollection;
import org.apache.beam.sdk.values.Row;

import org.checkerframework.checker.nullness.qual.NonNull;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Adds a prefix to a field in Row.
 *
 * If the field is not found the row is not changed.
 */
public class FieldPrefixAdderTransform extends PTransform<PCollection<Row>, PCollection<Row>> {

  private static final Logger logger = LoggerFactory.getLogger(FieldPrefixAdderTransform.class);

  private final String prefix;
  private final String fieldName;

  private FieldPrefixAdderTransform(String fieldName, String prefix) {
    this.fieldName = fieldName;
    this.prefix = prefix;
  }

  /**
   * Constructor method to create the transform
   *
   * @return constructed transform
   */
  public static FieldPrefixAdderTransform create(@NonNull String fieldName,
      @NonNull String prefix) {
    return new FieldPrefixAdderTransform(fieldName, prefix);
  }

  static class FieldPrefixAdderDoFn extends DoFn<Row, Row> {

    private final String prefix;
    private final String fieldName;

    FieldPrefixAdderDoFn(String fieldName, String prefix) {
      this.fieldName = fieldName;
      this.prefix = prefix;
    }

    @ProcessElement
    public void process(@Element Row input, OutputReceiver<Row> o) {
      String original;
      try {
        original = input.getString(fieldName);
      } catch (IllegalArgumentException e) {
          // In production pipelines a separate output should be used
          logger.error("Java: can't find field named '" + fieldName + "'");
          o.output(input);
          return;
      }
      // This is for illustration only. Logging in production pipelines shouldn't be used.
      logger.info("Java: added a prefix to value " + original);

      String newValue = prefix + original;
      Row result = Row.fromRow(input).withFieldValue(fieldName, newValue).build();
      o.output(result);
    }
  }

  @Override
  public PCollection<Row> expand(PCollection<Row> input) {
    Schema tableSchema = input.getSchema();
    return input.apply("Prefix " + fieldName, ParDo.of(new FieldPrefixAdderDoFn(fieldName, prefix)))
        .setRowSchema(tableSchema);
  }
}
