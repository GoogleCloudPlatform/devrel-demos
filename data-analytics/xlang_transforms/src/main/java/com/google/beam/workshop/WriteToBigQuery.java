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

import com.google.api.services.bigquery.model.TableRow;
import org.apache.beam.sdk.io.gcp.bigquery.BigQueryIO;
import org.apache.beam.sdk.io.gcp.bigquery.BigQueryIO.Write;
import org.apache.beam.sdk.io.gcp.bigquery.BigQueryIO.Write.CreateDisposition;
import org.apache.beam.sdk.io.gcp.bigquery.BigQueryIO.Write.WriteDisposition;
import org.apache.beam.sdk.io.gcp.bigquery.BigQueryUtils;
import org.apache.beam.sdk.schemas.Schema;
import org.apache.beam.sdk.transforms.MapElements;
import org.apache.beam.sdk.transforms.PTransform;
import org.apache.beam.sdk.transforms.SimpleFunction;
import org.apache.beam.sdk.values.PCollection;
import org.apache.beam.sdk.values.PDone;
import org.apache.beam.sdk.values.Row;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 */
public class WriteToBigQuery extends PTransform<PCollection<Row>, PDone> {

  private static final Logger logger = LoggerFactory.getLogger(WriteToBigQuery.class);

  private String tableName;
  private Write.Method method = Write.Method.DEFAULT;

  private WriteToBigQuery(String tableName) {
    this.tableName = tableName;
  }

  /**
   * Constructor method to create the transform
   *
   * @return constructed transform
   */
  public static WriteToBigQuery writeTo(String tableName) {
    return new WriteToBigQuery(tableName);
  }

  public WriteToBigQuery usingStorageApiAtLeastOnceMethod() {
    method = Write.Method.STORAGE_API_AT_LEAST_ONCE;
    return this;
  }

  public WriteToBigQuery usingStorageWriteExactlyOnceMethod() {
    method = Write.Method.STORAGE_WRITE_API;
    return this;
  }

  @Override
  public PDone expand(PCollection<Row> input) {
    Schema inputSchema = input.getSchema();

    input
        .apply("To TableRow", MapElements.via(
            new SimpleFunction<Row, TableRow>() {
              @Override
              public TableRow apply(Row input) {
                return BigQueryUtils.toTableRow(input);
              }
            }
        ))
        .apply("Write to BigQuery", BigQueryIO.writeTableRows()
            .to(tableName)
            .withSchema(BigQueryUtils.toTableSchema(inputSchema))
            .withWriteDisposition(WriteDisposition.WRITE_APPEND)
            .withCreateDisposition(CreateDisposition.CREATE_IF_NEEDED)
            .withMethod(method)
        );
    return PDone.in(input.getPipeline());
  }
}
