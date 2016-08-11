This is a collection of scripts to cluster UI layouts produced by Rico.


## Requirements
* Keras
* PIL
* Theano
* scikit-learn

### Usage

Convert the view hierarchies from XML to the JSON format used by Rico.
```bash
python convert_view_hierarchy_format.py <absolute_path_to_data_folder>
 ```

Represent each UI with an image with three separate segments for text elements,
icons and images.
```bash
python create_ui_representation.py <absolute_path_to_data_folder>
 ```

Combine these images into one numpy array that can be used for training an
autoencoder.
```bash
python create_ae_inputs.py
 ```

Train the autoencoder.
```bash
python train_ae.py
 ```

Reconstruct the input images from the compressed representation produced by the
autoencoder. Output images will be located in the `reconstructed_imgs` folder
for inspection.
```bash
python visualize_ae_reconstruction.py
 ```

Run k-means clustering on the encoded images for the images.
```bash
python run_kmeans.py
 ```

Produce HTML files to visualize the UI clusters. HTML files will be located in
`cluster_viz` folder for inspection.
```bash
python create_uv_map.py
python visualize_clusters.py <absolute_path_to_data_folder>
 ```
