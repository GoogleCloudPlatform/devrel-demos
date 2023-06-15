package beam.workshop;

import org.apache.beam.sdk.transforms.PTransform;
import org.apache.beam.sdk.values.PCollection;
import org.apache.beam.sdk.values.Row;

/**
 * Transform template
 */
public class CustomTransform extends PTransform<PCollection<Row>, PCollection<Row>> {

  @Override
  public PCollection<Row> expand(PCollection<Row> input) {
    return null;
  }
}
