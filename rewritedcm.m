function rewritedcm(expfolder,niifile)
% REWRITEDCM - input expfolder to read dicoms from, nifit data to rewrite
%              saves new dicoms in subdirctory (mlBrainStrip_) of given nifti
%              with series number +200
% TODO: params for outputdir, DCM pattern, +protocolnumber

   addpath('/opt/ni_tools/NlfTI/')
   
% rewritedcm('/Volumes/Disk_C/Temp/20170929Luna/DICOM/MP2RAGE_SCOUT/','/Users/lncd/Desktop/slice_warps/david_20170929/anatAndSlice.nii.gz')

    oldpwd=pwd();
    %niidir=cd(cd(fileparts(niifile))); % try to be absolute
    niidir=fileparts(niifile); % relative is not so bad
    savein = [ niidir '/' ];   

    cd(expfolder)
    % MP2RGAW 2nd TI image
    optupdown = 1; %1;          % slice order
    maxintensity = 1000;%1000   % ### adjust the value to make 3D rendering better w/o threshold in Siemens 3D    
    bartthreh = 0.5;
    winsize = 3;

    % chen codE:
    %P = [pfolder t1fname]; t1data = load_untouch_nii(P); t1img = double(t1data.img);
    img = load_untouch_nii(niifile);
    Y = double(img.img); % 96 x 118 x 128

    strfileext = '*.IMA';
    [nfiles,files] = dicom_filelist(strfileext);
    
    uid = dicomuid;
    disp('DICOM conversion - ');
    disp(pwd);
    fprintf('have %d files in %s\n',nfiles,expfolder );
    for ll=1:nfiles
        % ;;DICOM read
         
         sliceidx=nfiles-ll +1;
         strfile=files{sliceidx};

         if( mod(sliceidx,10) == 0)
            fprintf('slice %d, %s\n',sliceidx,strfile)
         end

         info = dicominfo(strfile);

         % python
         %   ndataford = numpy.fliplr( numpy.flipud( niidata[(ndcm-1-i),:,:].transpose() ) )
         %data = int16(Y(:,:,ll));
         %data = int16(fliplr(Y(:,:,ll)));
         %data = int16(flipud( fliplr( Y(:,:,ll) ))  ); % -90

         % readdicom(strfile) == 128x118, nfiles=96
         % Y = 96x118x128

         % data = dicomread(info); % if we were just making a copy
         slice=squeeze(Y(sliceidx,:,:));
         data = int16(  fliplr( flipud( slice' ))  );

         % ;;SeriesDescription
         SeriesDescription_ = ['mlBrainStrip_' info.SeriesDescription];
         
         
         % ;;Series update
         info.SeriesNumber       = info.SeriesNumber + 200;
         info.SeriesDescription  = SeriesDescription_;
         info.SeriesInstanceUID  =  uid;
         
         % ;;New folder generation
         newfolder = [savein SeriesDescription_];%
         if (ll==1),
             str_command = ['mkdir ' newfolder]; 
             [status,result] = system(str_command); %disp(str_command); 
         end
         % ;;Save
         info.SmallestImagePixelValue = 0;
         info.LargestImagePixelValue = maxintensity;

         %info.WindowCenter = meanval;
         %info.WindowWidth = 4*stdval;
         writeto=[newfolder '/' strfile ];
         %writeto=['/Users/lncd/Desktop/dcmcp/' strfile]
         dicomwrite(data, writeto, info); 

    end
    
    cd(oldpwd)
end

function [n,f] = dicom_filelist(patt)
  f=strsplit(ls(patt));
  keepidx=cellfun(@(x) ~isempty(x), f);
  n=nnz(keepidx);
  f=f(keepidx);
end
