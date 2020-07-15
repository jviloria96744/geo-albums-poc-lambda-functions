# GeoAlbums Lambda Functions

These are the two lambda functions that sit behind the [GeoAlbums](https://d2cndobv2blzcj.cloudfront.net/) web application. The front-end is a React App that uses Hooks and the Context API. The photo and user files correspond to the photo and user Context defined in that [codebase](https://github.com/jviloria96744/geo-albums).

## Dependencies

`user_lambda.py` has no dependencies. `photo_lambda.py` depends on the Requests, Pillow and Exif-Read packages. I made those packages into layers and do not include the zip files here.

## Further Development

The initial iteration of this application should be thought of as a POC as I have already realized some implementation changes I want to make. These functions should therefore also be thought of as terminal functions that will not see further development.

Further enhancements will be done through SAM/CDK or CloudFormation templates in a more repeatable way.
